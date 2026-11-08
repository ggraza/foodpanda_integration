"""Mock provider: behaves like Foodpanda, but nothing leaves your server.

Use it to build and test everything before Foodpanda approves the integration.
Every mock call is still written to Foodpanda API Log (URL starts with mock://),
so you can see exactly what the app would have sent.
"""

import time

import frappe
from frappe import _
from frappe.utils import now_datetime

from foodpanda_integration.client.api_log import write_api_log
from foodpanda_integration.constants import PROVIDER_MOCK
from foodpanda_integration.exceptions import FoodpandaAPIError
from foodpanda_integration.providers.base import BaseProvider

AVAILABILITY_STATES = ("OPEN", "CLOSED", "CLOSED_UNTIL", "CLOSED_TODAY", "UNKNOWN")


class MockProvider(BaseProvider):
	name = PROVIDER_MOCK

	def _call(self, operation, method, path, request=None, response=None):
		started = time.monotonic()
		fail = self._simulate_failure()
		write_api_log(
			account=self.account.name,
			restaurant=self.restaurant,
			operation=operation,
			method=method,
			url=f"mock://foodpanda{path}",
			request_body=request,
			status_code=503 if fail else 200,
			response_body={"error": "Simulated failure"} if fail else response,
			duration_ms=int((time.monotonic() - started) * 1000),
			success=not fail,
			error="Simulated failure (Mock)" if fail else None,
		)
		if fail:
			raise FoodpandaAPIError(_("Mock provider: simulated failure for {0}.").format(operation), 503)
		return response

	def _simulate_failure(self):
		# Lets a tester force an error: tick "Mock: Simulate Failure" on the account.
		return bool(self.account.get("mock_simulate_failure"))

	def _fail_before_change(self, operation, method, path, request):
		"""On a simulated failure, log and raise BEFORE changing any mock state."""
		if self._simulate_failure():
			self._call(operation, method, path, request)

	def _cache_key(self, *parts):
		# The account's creation time is part of the key, so a deleted and re-created
		# account with the same name starts with clean mock data.
		return "foodpanda_mock:" + ":".join([self.account.name, str(self.account.creation), *map(str, parts)])

	# --- Connection -----------------------------------------------------------
	def test_connection(self):
		self._call(
			"Test Connection", "POST", "/login", {"username": self.account.username or "mock"}, {"ok": True}
		)
		return {"ok": True, "message": _("Mock connection successful. No data was sent to Foodpanda.")}

	# --- Orders ---------------------------------------------------------------
	def update_order_status(self, order_token, status, reason=None, extra=None):
		body = {"status": status, "reason": reason, **(extra or {})}
		return self._call(
			"Update Order Status", "POST", f"/orders/{order_token}/status", body, {"accepted": True}
		)

	def mark_order_prepared(self, order_token):
		return self._call(
			"Mark Order Prepared", "POST", f"/v2/orders/{order_token}/preparation-completed", None, None
		)

	def get_order_ids(self, pos_vendor_id=None, status=None, past_hours=24):
		params = {"vendorId": pos_vendor_id, "status": status, "pastNumberOfHours": past_hours}
		return self._call("Get Order IDs", "GET", "/v2/chains/mock/orders/ids", params, {"orders": []})

	def get_order_detail(self, order_id):
		return self._call(
			"Get Order Detail", "GET", f"/v2/chains/mock/orders/{order_id}", None, {"order": {"id": order_id}}
		)

	# --- Menu and availability ------------------------------------------------
	def submit_catalog(self, pos_vendor_id, catalog):
		response = {"status": "submitted", "importId": frappe.generate_hash(length=12)}
		return self._call("Submit Catalog", "PUT", f"/catalog/{pos_vendor_id}", catalog, response)

	def get_import_logs(self, pos_vendor_id):
		return self._call(
			"Get Catalog Import Logs", "GET", f"/vendors/{pos_vendor_id}/menu-import-logs", None, []
		)

	def update_item_availability(self, pos_vendor_id, items):
		path = f"/vendors/{pos_vendor_id}/items/availability"
		self._fail_before_change("Update Item Availability", "POST", path, items)
		key = self._cache_key("unavailable", pos_vendor_id)
		unavailable = set(frappe.cache().get_value(key) or [])
		for item in items:
			if item.get("available"):
				unavailable.discard(item["remote_code"])
			else:
				unavailable.add(item["remote_code"])
		frappe.cache().set_value(key, sorted(unavailable))
		return self._call(
			"Update Item Availability",
			"POST",
			f"/vendors/{pos_vendor_id}/items/availability",
			items,
			{"ok": True},
		)

	def get_unavailable_items(self, pos_vendor_id):
		unavailable = frappe.cache().get_value(self._cache_key("unavailable", pos_vendor_id)) or []
		return self._call(
			"Get Unavailable Items",
			"GET",
			f"/vendors/{pos_vendor_id}/catalog/items/unavailable",
			None,
			unavailable,
		)

	def get_vendor_availability(self, pos_vendor_id):
		state = frappe.cache().get_value(self._cache_key("availability", pos_vendor_id)) or {
			"availabilityState": "OPEN"
		}
		return self._call(
			"Get Vendor Availability", "GET", f"/remoteVendors/{pos_vendor_id}/availability", None, state
		)

	def update_vendor_availability(self, pos_vendor_id, availability_state, closing_reason=None):
		if availability_state not in AVAILABILITY_STATES:
			raise FoodpandaAPIError(_("Invalid availability state: {0}").format(availability_state), 400)
		path = f"/remoteVendors/{pos_vendor_id}/availability"
		state = {
			"availabilityState": availability_state,
			"closingReason": closing_reason,
			"changedAt": str(now_datetime()),
		}
		self._fail_before_change("Update Vendor Availability", "PUT", path, state)
		frappe.cache().set_value(self._cache_key("availability", pos_vendor_id), state)
		return self._call("Update Vendor Availability", "PUT", path, state, state)
