"""Helpers shared by the Foodpanda tests. Works on Frappe v14, v15 and v16."""

import frappe

try:  # Frappe v15.? and v16
	from frappe.tests import IntegrationTestCase as FoodpandaTestCase
except ImportError:  # Frappe v14 / v15
	from frappe.tests.utils import FrappeTestCase as FoodpandaTestCase

TEST_COMPANY = "Foodpanda Test Company"


def make_company(name=TEST_COMPANY, abbr="FPTC"):
	if not frappe.db.exists("Company", name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": name,
				"abbr": abbr,
				"default_currency": "PKR",
				"country": "Pakistan",
			}
		).insert(ignore_permissions=True)
	return name


def make_account(name="FP Test Mock", provider="Mock", **kwargs):
	if frappe.db.exists("Foodpanda Account", name):
		frappe.delete_doc("Foodpanda Account", name, force=True)
	doc = frappe.get_doc(
		{"doctype": "Foodpanda Account", "account_name": name, "provider": provider, **kwargs}
	)
	return doc.insert(ignore_permissions=True)


def set_settings(**values):
	settings = frappe.get_single("Foodpanda Settings")
	settings.update(values)
	settings.save(ignore_permissions=True)


__all__ = ["FoodpandaTestCase", "make_account", "make_company", "set_settings", "TEST_COMPANY"]
