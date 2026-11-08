"""Provider layer: the only place that knows how to talk to Foodpanda.

    from foodpanda_integration.providers import get_provider
    provider = get_provider("My Foodpanda Account")
    provider.test_connection()

Two providers exist:
- "Mock": a fake Foodpanda used for development and testing. Always available.
- "Delivery Hero": the real Foodpanda / Delivery Hero POS Middleware API.
  It stays switched off until "Enable Live Foodpanda API" is ticked in Foodpanda Settings,
  which should only be done after Foodpanda has approved the integration and issued credentials.
"""

import frappe
from frappe import _

from foodpanda_integration.constants import PROVIDER_DELIVERY_HERO, PROVIDER_MOCK
from foodpanda_integration.exceptions import FoodpandaConfigError, FoodpandaLiveAPIDisabled


def _registry():
	# Imported here so the live adapter module is only loaded when it is really needed.
	from foodpanda_integration.providers.delivery_hero import DeliveryHeroProvider
	from foodpanda_integration.providers.mock import MockProvider

	return {PROVIDER_MOCK: MockProvider, PROVIDER_DELIVERY_HERO: DeliveryHeroProvider}


def is_live_api_enabled():
	return bool(frappe.db.get_single_value("Foodpanda Settings", "enable_live_api"))


def get_provider(account, restaurant=None):
	"""Return the provider object for a Foodpanda Account (name or document)."""
	account_doc = account if not isinstance(account, str) else frappe.get_doc("Foodpanda Account", account)

	if not frappe.db.get_single_value("Foodpanda Settings", "enabled"):
		raise FoodpandaConfigError(_("Foodpanda Integration is disabled in Foodpanda Settings."))
	if not account_doc.enabled:
		raise FoodpandaConfigError(_("Foodpanda Account {0} is disabled.").format(account_doc.name))

	provider_class = _registry().get(account_doc.provider)
	if not provider_class:
		raise FoodpandaConfigError(_("Unknown provider: {0}").format(account_doc.provider))

	if account_doc.provider != PROVIDER_MOCK and not is_live_api_enabled():
		raise FoodpandaLiveAPIDisabled(
			_(
				"The live Foodpanda API is switched off. Use the Mock provider, or tick "
				"'Enable Live Foodpanda API' in Foodpanda Settings after Foodpanda approves your integration."
			)
		)
	return provider_class(account_doc, restaurant=restaurant)
