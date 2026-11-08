"""Real Foodpanda adapter: Delivery Hero POS Integration Middleware API.

THIS ADAPTER IS SWITCHED OFF BY DEFAULT.
It is only used when both are true:
  1. the Foodpanda Account's Provider is "Delivery Hero", and
  2. "Enable Live Foodpanda API" is ticked in Foodpanda Settings.
Do that only after Foodpanda has approved the integration and sent you credentials.

What is implemented here, and why
---------------------------------
Only operations named in the official public documentation are implemented:
  https://integration.foodpanda.com/en/documentation/
  https://developers.deliveryhero.com/documentation/pos.html

* Endpoints whose exact path is public use that path by default (see constants.VERIFIED_ENDPOINTS).
* Endpoints whose path or request body is NOT public (login, order status update, catalog submit,
  item / vendor availability update) read their path from the Foodpanda Account. Their request
  body must be checked against the official API spec you receive with your credentials
  (roadmap Phase 9). Until a path is filled in, calling it raises a clear configuration error,
  so nothing is ever sent to a guessed endpoint.
"""

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime
from frappe.utils.password import set_encrypted_password

from foodpanda_integration.client.http import FoodpandaHttpClient, build_path, get_password
from foodpanda_integration.constants import PROVIDER_DELIVERY_HERO, VERIFIED_ENDPOINTS
from foodpanda_integration.exceptions import (
	FoodpandaAPIError,
	FoodpandaConfigError,
	FoodpandaLiveAPIDisabled,
)
from foodpanda_integration.providers.base import BaseProvider

TOKEN_SAFETY_MARGIN_SECONDS = 60


class DeliveryHeroProvider(BaseProvider):
	name = PROVIDER_DELIVERY_HERO

	def __init__(self, account_doc, restaurant=None):
		super().__init__(account_doc, restaurant)
		self._check_live_switch()
		self.client = FoodpandaHttpClient(account_doc, restaurant=restaurant)

	@staticmethod
	def _check_live_switch():
		"""Checked before every request, so turning the switch off stops calls immediately."""
		from foodpanda_integration.providers import is_live_api_enabled

		if not is_live_api_enabled():
			raise FoodpandaLiveAPIDisabled(_("The live Foodpanda API is switched off in Foodpanda Settings."))

	# --- helpers ----------------------------------------------------------------
	def _path(self, fieldname, **values):
		template = self.account.get(fieldname) or VERIFIED_ENDPOINTS.get(fieldname)
		if not template:
			label = self.account.meta.get_label(fieldname)
			raise FoodpandaConfigError(
				_(
					"'{0}' is not set on Foodpanda Account {1}. Copy it from the official Delivery Hero "
					"API specification you received from Foodpanda."
				).format(label, self.account.name)
			)
		values.setdefault("chain_code", self.account.chain_code or "")
		return build_path(template, **values)

	def _token(self, force_refresh=False):
		"""Return a valid access token, logging in again when it has expired."""
		token = get_password(self.account, "access_token")
		expires = self.account.token_expires_at
		if token and expires and not force_refresh and get_datetime(expires) > now_datetime():
			return token
		return self._login()

	def _login(self):
		username = self.account.username
		password = get_password(self.account, "password")
		if not username or not password:
			raise FoodpandaConfigError(_("Username and Password are required on the Foodpanda Account."))

		self._check_live_switch()
		# Request format to be confirmed against the official spec in Phase 9.
		body = self.client.request(
			"POST",
			self._path("login_path"),
			operation="Login",
			data={"username": username, "password": password, "grant_type": "client_credentials"},
			headers={"Content-Type": "application/x-www-form-urlencoded"},
		)
		token = (body or {}).get("access_token")
		if not token:
			raise FoodpandaAPIError(_("Login answered without an access token."))
		lifetime = int((body or {}).get("expires_in") or 3600)
		expires_at = add_to_date(now_datetime(), seconds=max(lifetime - TOKEN_SAFETY_MARGIN_SECONDS, 60))
		# Store the token encrypted (like any Password field) and keep only a mask in the column.
		set_encrypted_password("Foodpanda Account", self.account.name, token, "access_token")
		frappe.db.set_value(
			"Foodpanda Account",
			self.account.name,
			{"access_token": "*" * 10, "token_expires_at": expires_at},
			update_modified=False,
		)
		self.account.access_token = "*" * 10
		self.account.token_expires_at = expires_at
		return token

	def _request(self, method, path, operation, **kwargs):
		self._check_live_switch()
		try:
			return self.client.request(method, path, operation=operation, auth_token=self._token(), **kwargs)
		except FoodpandaAPIError as e:
			if e.status_code == 401:  # token expired early: log in once more and retry
				return self.client.request(
					method, path, operation=operation, auth_token=self._token(force_refresh=True), **kwargs
				)
			raise

	def _needs_official_body(self, operation):
		raise FoodpandaConfigError(
			_(
				"{0} is not activated yet. Its request body must be taken from the official Delivery Hero "
				"API specification (roadmap Phase 9)."
			).format(operation)
		)

	# --- Connection -----------------------------------------------------------
	def test_connection(self):
		self._token(force_refresh=True)
		return {"ok": True, "message": _("Logged in to Foodpanda successfully.")}

	# --- Orders ---------------------------------------------------------------
	def update_order_status(self, order_token, status, reason=None, extra=None):
		self._path("order_status_path", order_token=order_token)
		self._needs_official_body("Update Order Status")

	def mark_order_prepared(self, order_token):
		path = self._path("preparation_completed_path", order_token=order_token)
		return self._request("POST", path, "Mark Order Prepared", redact=[order_token])

	def get_order_ids(self, pos_vendor_id=None, status=None, past_hours=24):
		params = {"pastNumberOfHours": past_hours}
		if status:
			params["status"] = status
		if pos_vendor_id:
			params["vendorId"] = pos_vendor_id
		return self._request("GET", self._path("order_ids_path"), "Get Order IDs", params=params)

	def get_order_detail(self, order_id):
		return self._request("GET", self._path("order_detail_path", order_id=order_id), "Get Order Detail")

	# --- Menu and availability ------------------------------------------------
	def submit_catalog(self, pos_vendor_id, catalog):
		self._path("catalog_submit_path", pos_vendor_id=pos_vendor_id)
		self._needs_official_body("Submit Catalog")

	def get_import_logs(self, pos_vendor_id):
		path = self._path("import_logs_path", pos_vendor_id=pos_vendor_id)
		return self._request("GET", path, "Get Catalog Import Logs")

	def update_item_availability(self, pos_vendor_id, items):
		self._path("item_availability_path", pos_vendor_id=pos_vendor_id)
		self._needs_official_body("Update Item Availability")

	def get_unavailable_items(self, pos_vendor_id):
		path = self._path("unavailable_items_path", pos_vendor_id=pos_vendor_id)
		return self._request("GET", path, "Get Unavailable Items")

	def get_vendor_availability(self, pos_vendor_id):
		path = self._path("vendor_availability_path", pos_vendor_id=pos_vendor_id)
		return self._request("GET", path, "Get Vendor Availability")

	def update_vendor_availability(self, pos_vendor_id, availability_state, closing_reason=None):
		self._path("vendor_availability_update_path", pos_vendor_id=pos_vendor_id)
		self._needs_official_body("Update Vendor Availability")
