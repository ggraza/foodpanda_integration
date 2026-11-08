"""The interface every provider implements.

Phase 1 only uses test_connection(). The other methods are declared now so that later
phases (orders, statuses, menu, stock) can be written once against this interface.
A provider that cannot do something raises FoodpandaNotSupported.
"""

from frappe import _

from foodpanda_integration.exceptions import FoodpandaNotSupported


class BaseProvider:
	name = "Base"

	def __init__(self, account_doc, restaurant=None):
		self.account = account_doc
		self.restaurant = restaurant  # Foodpanda Restaurant name, optional

	def _not_supported(self, operation):
		raise FoodpandaNotSupported(
			_("{0} is not supported by the {1} provider.").format(operation, self.name)
		)

	# --- Connection -----------------------------------------------------------
	def test_connection(self):
		"""Return a dict: {"ok": bool, "message": str}."""
		self._not_supported("Test Connection")

	# --- Orders (Phase 2-3) ---------------------------------------------------
	def update_order_status(self, order_token, status, reason=None, extra=None):
		self._not_supported("Update Order Status")

	def mark_order_prepared(self, order_token):
		self._not_supported("Mark Order Prepared")

	def get_order_ids(self, pos_vendor_id=None, status=None, past_hours=24):
		self._not_supported("Get Order IDs")

	def get_order_detail(self, order_id):
		self._not_supported("Get Order Detail")

	# --- Menu and availability (Phase 5-6) ------------------------------------
	def submit_catalog(self, pos_vendor_id, catalog):
		self._not_supported("Submit Catalog")

	def get_import_logs(self, pos_vendor_id):
		self._not_supported("Get Catalog Import Logs")

	def update_item_availability(self, pos_vendor_id, items):
		self._not_supported("Update Item Availability")

	def get_unavailable_items(self, pos_vendor_id):
		self._not_supported("Get Unavailable Items")

	def get_vendor_availability(self, pos_vendor_id):
		self._not_supported("Get Vendor Availability")

	def update_vendor_availability(self, pos_vendor_id, availability_state, closing_reason=None):
		self._not_supported("Update Vendor Availability")
