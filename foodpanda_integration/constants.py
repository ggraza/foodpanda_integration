"""Shared constants for the Foodpanda integration."""

ROLE_MANAGER = "Foodpanda Manager"
ROLE_OPERATOR = "Foodpanda Operator"
ROLE_VIEWER = "Foodpanda Viewer"
ALL_ROLES = (ROLE_MANAGER, ROLE_OPERATOR, ROLE_VIEWER)

PROVIDER_MOCK = "Mock"
PROVIDER_DELIVERY_HERO = "Delivery Hero"

# Internal order statuses, in the order an order normally moves through them.
STATUS_RECEIVED = "Received"
STATUS_PENDING = "Pending Acceptance"
STATUS_ACCEPTED = "Accepted"
STATUS_REJECTED = "Rejected"
STATUS_PREPARING = "Preparing"
STATUS_READY = "Ready for Pickup"
STATUS_PICKED_UP = "Picked Up"
STATUS_DELIVERED = "Delivered"
STATUS_CANCELLED = "Cancelled"
STATUS_FAILED = "Failed"

INTERNAL_STATUSES = (
	STATUS_RECEIVED,
	STATUS_PENDING,
	STATUS_ACCEPTED,
	STATUS_REJECTED,
	STATUS_PREPARING,
	STATUS_READY,
	STATUS_PICKED_UP,
	STATUS_DELIVERED,
	STATUS_CANCELLED,
	STATUS_FAILED,
)

# Default status map for a new Foodpanda Account.
# "foodpanda_status" values come from the public Delivery Hero POS docs where they are
# named ("order_accepted", "order_rejected"). Values the public docs do not spell out are
# left blank on purpose: fill them in from the official spec once Foodpanda grants access.
# Each row: (internal status, foodpanda status, direction, supported by the API)
DEFAULT_STATUS_MAP = (
	(STATUS_RECEIVED, "", "Inbound", 1),
	(STATUS_PENDING, "", "Internal", 0),
	(STATUS_ACCEPTED, "order_accepted", "Outbound", 1),
	(STATUS_REJECTED, "order_rejected", "Outbound", 1),
	(STATUS_PREPARING, "", "Internal", 0),
	(STATUS_READY, "", "Outbound", 1),
	(STATUS_PICKED_UP, "", "Outbound", 1),
	(STATUS_DELIVERED, "", "Internal", 0),
	(STATUS_CANCELLED, "", "Inbound", 1),
	(STATUS_FAILED, "", "Internal", 0),
)

# Endpoint paths confirmed on the public Delivery Hero documentation pages.
# Placeholders in {curly_braces} are filled in by the client.
# Paths that are NOT public (login, order status update, catalog submit, availability updates)
# are deliberately not listed: they are entered on the Foodpanda Account from the official spec.
VERIFIED_ENDPOINTS = {
	"preparation_completed_path": "/v2/orders/{order_token}/preparation-completed",
	"vendor_availability_path": "/v2/chains/{chain_code}/remoteVendors/{pos_vendor_id}/availability",
	"unavailable_items_path": "/v2/chains/{chain_code}/vendors/{pos_vendor_id}/catalog/items/unavailable",
	"import_logs_path": "/v2/chains/{chain_code}/vendors/{pos_vendor_id}/menu-import-logs",
	"order_ids_path": "/v2/chains/{chain_code}/orders/ids",
	"order_detail_path": "/v2/chains/{chain_code}/orders/{order_id}",
}

DELIVERY_HERO_STAGING_URL = "https://integration-middleware.stg.restaurant-partners.com"
