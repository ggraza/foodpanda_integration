# Copyright (c) 2026, Ghulam Ghous and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from foodpanda_integration.constants import (
	DEFAULT_STATUS_MAP,
	DELIVERY_HERO_STAGING_URL,
	PROVIDER_DELIVERY_HERO,
)


class FoodpandaAccount(Document):
	def before_insert(self):
		self.set_default_status_map()

	def validate(self):
		self.base_url = (self.base_url or "").strip().rstrip("/")
		if self.provider == PROVIDER_DELIVERY_HERO:
			if not self.base_url and self.environment == "Staging":
				self.base_url = DELIVERY_HERO_STAGING_URL
			if self.base_url:
				from foodpanda_integration.client.http import validate_base_url

				validate_base_url(self.base_url, resolve=False)
		self.validate_status_map()
		self.validate_allowed_ips()
		self.clear_token_if_credentials_changed()

	def clear_token_if_credentials_changed(self):
		"""A cached login token must not outlive the credentials or chain it was issued for."""
		if self.is_new():
			return
		watched = (
			"provider",
			"environment",
			"base_url",
			"chain_code",
			"username",
			"password",
			"client_secret",
		)
		if any(self.has_value_changed(field) for field in watched):
			self.access_token = None
			self.token_expires_at = None

	def set_default_status_map(self):
		if self.status_map:
			return
		for internal, foodpanda, direction, supported in DEFAULT_STATUS_MAP:
			self.append(
				"status_map",
				{
					"internal_status": internal,
					"foodpanda_status": foodpanda,
					"direction": direction,
					"supported": supported,
				},
			)

	def validate_status_map(self):
		seen_internal, seen_foodpanda = set(), set()
		for row in self.status_map:
			row.foodpanda_status = (row.foodpanda_status or "").strip()
			if row.internal_status in seen_internal:
				frappe.throw(_("Row {0}: status {1} is mapped twice.").format(row.idx, row.internal_status))
			seen_internal.add(row.internal_status)
			if row.foodpanda_status:
				if row.foodpanda_status in seen_foodpanda:
					frappe.throw(
						_("Row {0}: Foodpanda status {1} is used for more than one internal status.").format(
							row.idx, row.foodpanda_status
						)
					)
				seen_foodpanda.add(row.foodpanda_status)

	def validate_allowed_ips(self):
		import ipaddress

		for line in (self.allowed_ips or "").splitlines():
			ip = line.strip()
			if not ip:
				continue
			try:
				ipaddress.ip_network(ip, strict=False)
			except ValueError:
				frappe.throw(_("'{0}' is not a valid IP address.").format(ip))

	def get_allowed_ips(self):
		return [line.strip() for line in (self.allowed_ips or "").splitlines() if line.strip()]

	def get_foodpanda_status(self, internal_status):
		"""Internal status -> Foodpanda value (or None when Foodpanda has no equivalent)."""
		for row in self.status_map:
			if row.internal_status == internal_status:
				return row.foodpanda_status or None
		return None

	def get_internal_status(self, foodpanda_status):
		"""Foodpanda value -> internal status (or None when not mapped)."""
		for row in self.status_map:
			if row.foodpanda_status and row.foodpanda_status == foodpanda_status:
				return row.internal_status
		return None

	@frappe.whitelist()
	def test_connection(self):
		"""Called by the 'Test Connection' button. Only Managers can run it."""
		frappe.only_for(("Foodpanda Manager", "System Manager"))
		from foodpanda_integration.providers import get_provider

		try:
			result = get_provider(self).test_connection()
			status, message = "Success", result.get("message")
		except frappe.ValidationError as e:
			status, message = "Failed", str(e)
		except Exception as e:
			frappe.log_error(title="Foodpanda: Test Connection failed")
			status, message = "Failed", _("Unexpected error: {0}").format(e)

		self.db_set(
			{
				"last_connection_status": status,
				"last_connection_at": now_datetime(),
				"last_connection_message": message,
			}
		)
		return {"ok": status == "Success", "message": message}
