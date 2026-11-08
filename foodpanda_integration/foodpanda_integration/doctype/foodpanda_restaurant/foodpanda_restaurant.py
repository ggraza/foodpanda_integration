# Copyright (c) 2026, Ghulam Ghous and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FoodpandaRestaurant(Document):
	def validate(self):
		self.pos_vendor_id = (self.pos_vendor_id or "").strip()
		self.validate_unique_vendor()
		self.validate_company_links()

	def validate_unique_vendor(self):
		"""One Foodpanda vendor can only be linked to one restaurant per account."""
		duplicate = frappe.db.exists(
			"Foodpanda Restaurant",
			{"account": self.account, "pos_vendor_id": self.pos_vendor_id, "name": ("!=", self.name)},
		)
		if duplicate:
			frappe.throw(
				_("POS Vendor ID {0} is already used by restaurant {1} on this account.").format(
					frappe.bold(self.pos_vendor_id), frappe.bold(duplicate)
				)
			)

	def validate_company_links(self):
		"""Warehouse, Cost Center and POS Profile must belong to the restaurant's company."""
		for fieldname, doctype in (
			("warehouse", "Warehouse"),
			("cost_center", "Cost Center"),
			("pos_profile", "POS Profile"),
		):
			value = self.get(fieldname)
			if not value:
				continue
			company = frappe.db.get_value(doctype, value, "company")
			if company and company != self.company:
				frappe.throw(
					_("{0} {1} belongs to company {2}, not {3}.").format(
						_(doctype), frappe.bold(value), frappe.bold(company), frappe.bold(self.company)
					)
				)
