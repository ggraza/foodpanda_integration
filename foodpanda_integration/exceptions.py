"""Exceptions raised by the Foodpanda integration.

They all inherit from frappe.ValidationError so that, when one reaches the browser,
the user sees a normal red error message instead of a server error page.
"""

import frappe


class FoodpandaError(frappe.ValidationError):
	"""Base class for every Foodpanda integration error."""


class FoodpandaConfigError(FoodpandaError):
	"""Something is missing or wrong in the Foodpanda Account or Settings."""


class FoodpandaLiveAPIDisabled(FoodpandaError):
	"""The real (live) Foodpanda API was used while it is switched off in Foodpanda Settings."""


class FoodpandaNotSupported(FoodpandaError):
	"""The selected provider does not support this operation."""


class FoodpandaAPIError(FoodpandaError):
	"""Foodpanda answered with an error, or could not be reached."""

	def __init__(self, message, status_code=None, response_text=None):
		super().__init__(message)
		self.status_code = status_code
		self.response_text = response_text
