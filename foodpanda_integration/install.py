"""Code that runs when the app is installed or the site is migrated."""

import frappe

from foodpanda_integration.constants import ALL_ROLES


def after_install():
	create_roles()
	create_default_settings()
	frappe.db.commit()


def after_migrate():
	# Safe to run many times: it only creates what is missing.
	create_roles()


def create_roles():
	"""Create the three Foodpanda roles if they do not exist yet."""
	for role_name in ALL_ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		role = frappe.new_doc("Role")
		role.role_name = role_name
		role.desk_access = 1
		role.insert(ignore_permissions=True)


def create_default_settings():
	"""Start in safe mode: integration on, live Foodpanda API off (Mock only)."""
	settings = frappe.get_single("Foodpanda Settings")
	settings.enabled = 1
	settings.enable_live_api = 0
	settings.log_retention_days = settings.log_retention_days or 30
	settings.save(ignore_permissions=True)
