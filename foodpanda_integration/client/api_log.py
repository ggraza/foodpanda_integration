"""Write one Foodpanda API Log row per call (inbound or outbound), always masked."""

import frappe

from foodpanda_integration.client.masking import mask_data, to_log_text


def write_api_log(
	*,
	account=None,
	restaurant=None,
	direction="Outbound",
	operation=None,
	method=None,
	url=None,
	request_headers=None,
	request_body=None,
	status_code=None,
	response_body=None,
	duration_ms=None,
	success=False,
	error=None,
):
	"""Insert a log row. Never raises: logging must not break the real work."""
	try:
		log = frappe.new_doc("Foodpanda API Log")
		log.update(
			{
				"account": account,
				"restaurant": restaurant,
				"direction": direction,
				"operation": operation,
				"method": method,
				"url": (url or "")[:500],
				"status_code": status_code,
				"duration_ms": duration_ms,
				"success": 1 if success else 0,
				"request_headers": to_log_text(mask_data(request_headers or {})),
				"request_body": to_log_text(request_body),
				"response_body": to_log_text(response_body),
				"error": (str(error) if error else "")[:2000],
			}
		)
		log.insert(ignore_permissions=True)
		# Keep the log even if the surrounding request fails and is rolled back.
		if not frappe.flags.in_test:
			frappe.db.commit()
		return log.name
	except Exception:
		frappe.log_error(title="Foodpanda: could not write API log")
		return None
