"""Reusable HTTP client for the Foodpanda (Delivery Hero) API.

Features: base URL per account, path placeholders, timeouts, retries with back-off on
temporary errors (HTTP 429 / 5xx / network errors), masked logging of every call.

Only server-side code uses this client. Credentials are never sent to the browser.
"""

import time

import frappe
import requests

from foodpanda_integration.client.api_log import write_api_log
from foodpanda_integration.exceptions import FoodpandaAPIError, FoodpandaConfigError

RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
BACKOFF_SECONDS = 1  # 1s, 2s, 4s ...
MAX_BACKOFF_SECONDS = 30


def build_path(path_template, **values):
	"""'/v2/orders/{order_token}' + order_token='abc' -> '/v2/orders/abc'."""
	if not path_template:
		raise FoodpandaConfigError("Endpoint path is empty.")
	try:
		return path_template.format(**{k: requests.utils.quote(str(v), safe="") for k, v in values.items()})
	except KeyError as e:
		raise FoodpandaConfigError(f"Endpoint path '{path_template}' needs a value for {e}.") from e


class FoodpandaHttpClient:
	def __init__(self, account_doc, restaurant=None, session=None):
		self.account = account_doc
		self.restaurant = restaurant
		self.base_url = (account_doc.base_url or "").rstrip("/")
		self.timeout = int(account_doc.timeout_seconds or DEFAULT_TIMEOUT)
		self.max_retries = int(
			account_doc.max_retries if account_doc.max_retries is not None else DEFAULT_RETRIES
		)
		self.session = session or requests.Session()
		if not self.base_url.startswith("https://"):
			raise FoodpandaConfigError("Base URL must start with https:// on the Foodpanda Account.")

	def request(
		self,
		method,
		path,
		*,
		operation,
		params=None,
		json=None,
		data=None,
		headers=None,
		auth_token=None,
		expected=(200, 201, 202, 204),
	):
		"""Send a request and return the parsed JSON body (or None for an empty body)."""
		url = f"{self.base_url}{path}"
		send_headers = {"Accept": "application/json"}
		if auth_token:
			send_headers["Authorization"] = f"Bearer {auth_token}"
		send_headers.update(headers or {})

		attempt = 0
		while True:
			attempt += 1
			started = time.monotonic()
			response = None
			error = None
			try:
				response = self.session.request(
					method,
					url,
					params=params,
					json=json,
					data=data,
					headers=send_headers,
					timeout=self.timeout,
				)
			except requests.RequestException as e:
				error = e

			duration_ms = int((time.monotonic() - started) * 1000)
			status = response.status_code if response is not None else None
			ok = response is not None and status in expected
			write_api_log(
				account=self.account.name,
				restaurant=self.restaurant,
				operation=operation,
				method=method,
				url=url,
				request_headers=send_headers,
				request_body=json if json is not None else data,
				status_code=status,
				response_body=response.text if response is not None else None,
				duration_ms=duration_ms,
				success=ok,
				error=error or (None if ok else f"Unexpected HTTP {status}"),
			)

			if ok:
				return _parse_body(response)

			temporary = error is not None or status in RETRY_STATUS_CODES
			if temporary and attempt <= self.max_retries:
				time.sleep(_backoff(attempt, response))
				continue

			if error is not None:
				raise FoodpandaAPIError(f"Could not reach Foodpanda ({operation}): {error}") from error
			raise FoodpandaAPIError(
				f"Foodpanda returned HTTP {status} for {operation}.",
				status_code=status,
				response_text=(response.text or "")[:1000],
			)


def _backoff(attempt, response):
	retry_after = response.headers.get("Retry-After") if response is not None else None
	if retry_after and str(retry_after).isdigit():
		return min(int(retry_after), MAX_BACKOFF_SECONDS)
	return min(BACKOFF_SECONDS * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)


def _parse_body(response):
	if response.status_code == 204 or not response.content:
		return None
	try:
		return response.json()
	except ValueError:
		return {"raw": response.text}


def get_password(doc, fieldname):
	"""Read an encrypted Password field without raising when it is empty."""
	return doc.get_password(fieldname, raise_exception=False) if doc.get(fieldname) else None


__all__ = ["FoodpandaHttpClient", "build_path", "get_password", "frappe"]
