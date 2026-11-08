# Copyright (c) 2026, Ghulam Ghous and contributors
# For license information, please see license.txt

import frappe

from foodpanda_integration.tests.utils import FoodpandaTestCase, make_account, make_company

# Do not let the Frappe test runner build its own ERPNext test records (Company, Warehouse, ...).
# The tests create exactly what they need. (test_ignore: v14/v15, IGNORE_...: v16)
test_ignore = ["Company", "Warehouse", "Cost Center", "Customer", "Price List", "POS Profile"]
IGNORE_TEST_RECORD_DEPENDENCIES = test_ignore


def make_restaurant(name, account, company, vendor_id, **kwargs):
	if frappe.db.exists("Foodpanda Restaurant", name):
		frappe.delete_doc("Foodpanda Restaurant", name, force=True)
	return frappe.get_doc(
		{
			"doctype": "Foodpanda Restaurant",
			"restaurant_name": name,
			"account": account,
			"company": company,
			"pos_vendor_id": vendor_id,
			**kwargs,
		}
	).insert(ignore_permissions=True)


class TestFoodpandaRestaurant(FoodpandaTestCase):
	def setUp(self):
		self.company = make_company()
		self.other_company = make_company("Foodpanda Other Company", "FPOC")
		self.account = make_account().name

	def test_vendor_id_unique_per_account(self):
		make_restaurant("FP Test Branch 1", self.account, self.company, "PK-001")
		self.assertRaises(
			frappe.ValidationError, make_restaurant, "FP Test Branch 2", self.account, self.company, "PK-001"
		)

	def test_database_unique_index(self):
		indexes = frappe.db.sql(
			"show index from `tabFoodpanda Restaurant` where Key_name='unique_account_vendor'", as_dict=True
		)
		self.assertEqual(sorted(i.Column_name for i in indexes), ["account", "pos_vendor_id"])

	def test_warehouse_must_match_company(self):
		other_warehouse = frappe.db.get_value("Warehouse", {"company": self.other_company, "is_group": 0})
		self.assertTrue(other_warehouse)
		self.assertRaises(
			frappe.ValidationError,
			make_restaurant,
			"FP Test Branch 3",
			self.account,
			self.company,
			"PK-003",
			warehouse=other_warehouse,
		)

	def test_multi_company(self):
		a = make_restaurant("FP Test Lahore", self.account, self.company, "PK-L1")
		b = make_restaurant("FP Test Karachi", self.account, self.other_company, "PK-K1")
		self.assertNotEqual(a.company, b.company)
