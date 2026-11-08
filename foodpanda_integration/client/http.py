"""Reusable HTTP client for the Foodpanda (Delivery Hero) API.

Features: base URL per account, path placeholders, timeouts, retries with back-off on
temporary errors, masked logging of every call.

Safety rules:
- HTTPS only, and the host must not resolve to a private / internal address.
- Redirects are never followed, so credentials can't be replayed to another host.
- Requests that change data (POST, PATCH) are retried only when the server said it did not
  process them (HTTP 429). GET / PUT / DELETE are safe to repeat and retry on 429, 5xx and
  network errors.

Only server-side code uses this client. Credentials are never sent to the browser.
"""

import ipaddress
import socket
import time
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import frappe
import requests
from frappe import _

from foodpanda_integration.client.api_log import write_api_log
from foodpanda_integration.exceptions import FoodpandaAPIError, FoodpandaConfigError

RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
IDEMPOTENT_METHODS = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
BACKOFF_SECONDS = 1  # 1s, 2s, 4s ...
MAX_BACKOFF_SECONDS = 30


def build_path(path_template, **values):
	"""'/v2/orders/{order_token}' + order_token='abc' -> '/v2/orders/abc'."""
	if not path_template:
		raise FoodpandaConfigError(_("Endpoint path is empty."))
	try:
		return path_template.format(**{k: requests.utils.quote(str(v), safe="") for k, v in values.items()})
	except KeyError as e:
		raise FoodpandaConfigError(
			_("Endpoint path '{0}' needs a value for {1}.").format(path_template, e)
		) from e


def validate_base_url(base_url, resolve=True):
	"""Allow only https:// URLs whose host is a public internet address.

	resolve=False skips the DNS lookup (used when saving the form, so it works offline);
	the lookup always happens right before a real request is sent.
	"""
	parsed = urlparse(base_url or "")
	host = parsed.hostname
	if parsed.scheme != "https" or not host:
		raise FoodpandaConfigError(_("API Base URL must start with https:// and include a host name."))

	def refuse():
		raise FoodpandaConfigError(
			_("API Base URL host {0} points to a private or internal address, which is not allowed.").format(
				host
			)
		)

	if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
		refuse()
	try:
		literal = ipaddress.ip_address(host)
	except ValueError:
		literal = None
	if literal is not None:
		if not literal.is_global:
			refuse()
		return
	if not resolve:
		return
	try:
		addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port or 443)}
	except socket.gaierror as e:
		raise FoodpandaConfigError(_("Cannot resolve host {0}.").format(host)) from e
	for address in addresses:
		if not ipaddress.ip_address(address.split("%")[0]).is_global:
			refuse()


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
		# Checked again before every request (DNS answers can change).
		validate_base_url(self.base_url, resolve=False)

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
		redact=None,
		expected=(200, 201, 202, 204),
	):
		"""Send a request and return the parsed JSON body (or None for an empty body).

		redact: values (for example an order token) to hide in the logged URL and error.
		"""
		method = method.upper()
		url = f"{self.base_url}{path}"
		validate_base_url(self.base_url, resolve=not frappe.flags.in_test)
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
					allow_redirects=False,
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
				redact=redact,
			)

			if ok:
				return _parse_body(response)

			if _should_retry(method, status, error) and attempt <= self.max_retries:
				time.sleep(_backoff(attempt, response))
				continue

			if error is not None:
				raise FoodpandaAPIError(
					_("Could not reach Foodpanda ({0}): {1}").format(operation, type(error).__name__)
				) from error
			raise FoodpandaAPIError(
				_("Foodpanda returned HTTP {0} for {1}.").format(status, operation),
				status_code=status,
				response_text=(response.text or "")[:1000],
			)


def _should_retry(method, status, error):
	if status == 429:  # the server did not process the request: always safe to retry
		return True
	if method not in IDEMPOTENT_METHODS:  # POST may already have been processed
		return False
	return error is not None or status in RETRY_STATUS_CODES


def _backoff(attempt, response):
	default = min(BACKOFF_SECONDS * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)
	retry_after = response.headers.get("Retry-After") if response is not None else None
	if not retry_after:
		return default
	retry_after = str(retry_after).strip()
	if retry_after.isdigit():
		return min(int(retry_after), MAX_BACKOFF_SECONDS)
	try:  # HTTP-date form, e.g. "Wed, 21 Oct 2026 07:28:00 GMT"
		when = parsedate_to_datetime(retry_after)
		seconds = when.timestamp() - time.time()
		return min(max(seconds, 0), MAX_BACKOFF_SECONDS)
	except (TypeError, ValueError):
		return default


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
