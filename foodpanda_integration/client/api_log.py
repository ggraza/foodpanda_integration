"""Write one Foodpanda API Log row per call (inbound or outbound), always masked."""

import frappe

from foodpanda_integration.client.masking import MASK, mask_data, mask_free_text, to_log_text


def _redact(text, values):
	text = str(text or "")
	for value in values or ():
		if value:
			text = text.replace(str(value), MASK)
	return text


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
	redact=None,
):
	"""Insert a log row. Never raises: logging must not break the real work.

	The row is written in the caller's transaction (no commit here). If that transaction is
	rolled back, the row is written again right after the rollback, so failed calls still
	leave a log without committing anything else the caller had changed.
	"""
	values = {
		"doctype": "Foodpanda API Log",
		"account": account,
		"restaurant": restaurant,
		"direction": direction,
		"operation": operation,
		"method": method,
		"url": _redact(mask_free_text(url or ""), redact)[:500],
		"status_code": status_code,
		"duration_ms": duration_ms,
		"success": 1 if success else 0,
		"request_headers": to_log_text(mask_data(request_headers or {})),
		"request_body": _redact(to_log_text(request_body), redact),
		"response_body": _redact(to_log_text(response_body), redact),
		"error": _redact(mask_free_text(str(error) if error else ""), redact)[:2000],
	}
	try:
		log = frappe.get_doc(values).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Foodpanda: could not write API log")
		return None

	_keep_after_rollback(values)
	return log.name


def _keep_after_rollback(values):
	"""Remember this row; if the transaction is rolled back, write all remembered rows again."""
	after_rollback = getattr(frappe.db, "after_rollback", None)
	if after_rollback is None or frappe.flags.in_test:
		return
	pending = getattr(frappe.local, "foodpanda_pending_logs", None)
	if pending is None:
		pending = frappe.local.foodpanda_pending_logs = []
		after_rollback.add(_write_after_rollback)
		# A successful commit keeps the rows already, so forget them then.
		frappe.db.after_commit.add(_forget_pending)
	pending.append(values)


def _forget_pending():
	frappe.local.foodpanda_pending_logs = None


def _write_after_rollback():
	"""Runs only after the caller's transaction was rolled back, so nothing else is pending."""
	pending = getattr(frappe.local, "foodpanda_pending_logs", None) or []
	frappe.local.foodpanda_pending_logs = None
	try:
		for values in pending:
			frappe.get_doc(dict(values)).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
