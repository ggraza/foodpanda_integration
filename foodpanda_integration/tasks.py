"""Functions called by the Frappe Scheduler (see scheduler_events in hooks.py)."""

import frappe
from frappe.utils import add_days, now_datetime


def cleanup_api_logs():
	"""Delete Foodpanda API Log rows older than the retention period in Foodpanda Settings."""
	days = frappe.db.get_single_value("Foodpanda Settings", "log_retention_days") or 30
	cutoff = add_days(now_datetime(), -int(days))
	frappe.db.delete("Foodpanda API Log", {"creation": ("<", cutoff)})
	frappe.db.commit()
