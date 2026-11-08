app_name = "foodpanda_integration"
app_title = "Foodpanda Integration"
app_publisher = "Ghulam Ghous"
app_description = "Foodpanda (Delivery Hero) restaurant integration for ERPNext and POSAwesome"
app_email = "ghulamghous.raza@gmail.com"
app_license = "MIT"

# ERPNext must be installed first (Company, Warehouse, Price List, ...).
required_apps = ["erpnext"]

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
# Creates the Foodpanda roles and default settings.
after_install = "foodpanda_integration.install.after_install"
after_migrate = "foodpanda_integration.install.after_migrate"

# ---------------------------------------------------------------------------
# Scheduled tasks (Frappe Scheduler)
# ---------------------------------------------------------------------------
scheduler_events = {
	"daily": [
		"foodpanda_integration.tasks.cleanup_api_logs",
	],
}

# ---------------------------------------------------------------------------
# Notes for later phases
# ---------------------------------------------------------------------------
# Phase 2 adds the plugin endpoints Foodpanda calls (orders, cancellations).
# Phase 4 adds the POSAwesome screen, loaded only when POSAwesome is installed.
# No ERPNext or POSAwesome core file is ever modified by this app.
