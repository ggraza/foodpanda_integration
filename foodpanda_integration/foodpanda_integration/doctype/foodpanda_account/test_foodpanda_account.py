# Copyright (c) 2026, Ghulam Ghous and contributors
# For license information, please see license.txt

import frappe

from foodpanda_integration.constants import INTERNAL_STATUSES
from foodpanda_integration.tests.utils import FoodpandaTestCase, make_account

# Do not let the Frappe test runner build its own ERPNext test records (Company, Warehouse, ...).
# The tests create exactly what they need. (test_ignore: v14/v15, IGNORE_...: v16)
test_ignore = ["Company", "Warehouse", "Cost Center", "Customer", "Price List", "POS Profile"]
IGNORE_TEST_RECORD_DEPENDENCIES = test_ignore


class TestFoodpandaAccount(FoodpandaTestCase):
	def test_default_status_map_created(self):
		account = make_account()
		self.assertEqual([row.internal_status for row in account.status_map], list(INTERNAL_STATUSES))
		self.assertEqual(account.get_foodpanda_status("Accepted"), "order_accepted")
		self.assertEqual(account.get_internal_status("order_rejected"), "Rejected")
		self.assertIsNone(account.get_foodpanda_status("Preparing"))

	def test_duplicate_status_rejected(self):
		account = make_account()
		account.append("status_map", {"internal_status": "Accepted"})
		self.assertRaises(frappe.ValidationError, account.save)

	def test_live_account_gets_staging_url_and_needs_https(self):
		account = make_account(name="FP Test Live", provider="Delivery Hero", environment="Staging")
		self.assertTrue(account.base_url.startswith("https://integration-middleware.stg"))
		account.base_url = "http://insecure.example"
		self.assertRaises(frappe.ValidationError, account.save)

	def test_invalid_ip_rejected(self):
		account = make_account()
		account.allowed_ips = "34.246.34.27\nnot-an-ip"
		self.assertRaises(frappe.ValidationError, account.save)

	def test_password_is_encrypted(self):
		account = make_account(name="FP Test Live", provider="Delivery Hero", password="secret-value")
		self.assertNotEqual(
			frappe.db.get_value("Foodpanda Account", account.name, "password"), "secret-value"
		)
		self.assertEqual(account.get_password("password"), "secret-value")
