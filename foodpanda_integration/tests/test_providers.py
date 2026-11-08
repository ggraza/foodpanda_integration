from unittest.mock import MagicMock, patch

import frappe

from foodpanda_integration.client.http import FoodpandaHttpClient, build_path
from foodpanda_integration.exceptions import (
	FoodpandaAPIError,
	FoodpandaConfigError,
	FoodpandaLiveAPIDisabled,
)
from foodpanda_integration.providers import get_provider
from foodpanda_integration.providers.mock import MockProvider
from foodpanda_integration.tests.utils import FoodpandaTestCase, make_account, set_settings

# Do not let the Frappe test runner build its own ERPNext test records (Company, Warehouse, ...).
# The tests create exactly what they need. (test_ignore: v14/v15, IGNORE_...: v16)
test_ignore = ["Company", "Warehouse", "Cost Center", "Customer", "Price List", "POS Profile"]
IGNORE_TEST_RECORD_DEPENDENCIES = test_ignore


class TestProviders(FoodpandaTestCase):
	def setUp(self):
		set_settings(enabled=1, enable_live_api=0)

	def test_mock_test_connection_succeeds_and_logs(self):
		account = make_account()
		result = account.test_connection()
		self.assertTrue(result["ok"])
		account.reload()
		self.assertEqual(account.last_connection_status, "Success")
		log = frappe.get_last_doc("Foodpanda API Log", filters={"account": account.name})
		self.assertTrue(log.url.startswith("mock://"))
		self.assertEqual(log.success, 1)

	def test_mock_simulated_failure(self):
		account = make_account(mock_simulate_failure=1)
		result = account.test_connection()
		self.assertFalse(result["ok"])
		self.assertEqual(
			frappe.db.get_value("Foodpanda Account", account.name, "last_connection_status"), "Failed"
		)

	def test_mock_vendor_availability_round_trip(self):
		provider = get_provider(make_account())
		provider.update_vendor_availability("V1", "CLOSED", "TOO_BUSY_KITCHEN")
		self.assertEqual(provider.get_vendor_availability("V1")["availabilityState"], "CLOSED")
		self.assertRaises(FoodpandaAPIError, provider.update_vendor_availability, "V1", "BAD")

	def test_live_provider_blocked_while_disabled(self):
		account = make_account(name="FP Test Live", provider="Delivery Hero", environment="Staging")
		self.assertRaises(FoodpandaLiveAPIDisabled, get_provider, account)
		result = account.test_connection()
		self.assertFalse(result["ok"])

	def test_integration_switched_off(self):
		account = make_account()
		set_settings(enabled=0)
		self.assertRaises(FoodpandaConfigError, get_provider, account)

	def test_get_provider_returns_mock(self):
		self.assertIsInstance(get_provider(make_account()), MockProvider)

	def test_live_provider_refuses_unconfigured_paths(self):
		set_settings(enable_live_api=1)
		account = make_account(name="FP Test Live", provider="Delivery Hero", username="u", password="p")
		provider = get_provider(account)
		# Login path is not public, so it must be configured before anything is sent.
		with patch.object(provider.client.session, "request") as request:
			self.assertRaises(FoodpandaConfigError, provider.test_connection)
			request.assert_not_called()

	def test_live_provider_login_and_token_cache(self):
		set_settings(enable_live_api=1)
		account = make_account(
			name="FP Test Live",
			provider="Delivery Hero",
			username="u",
			password="p",
			login_path="/login-from-spec",
		)
		provider = get_provider(account)
		response = MagicMock(status_code=200, content=b"{}", text='{"access_token": "tok"}')
		response.json.return_value = {"access_token": "tok", "expires_in": 3600}
		with patch.object(provider.client.session, "request", return_value=response) as request:
			self.assertTrue(provider.test_connection()["ok"])
			self.assertEqual(provider._token(), "tok")  # cached, no second login
			self.assertEqual(request.call_count, 1)
		# The token is stored encrypted, never in plain text.
		self.assertNotEqual(frappe.db.get_value("Foodpanda Account", account.name, "access_token"), "tok")
		log = frappe.get_last_doc("Foodpanda API Log", filters={"account": account.name})
		self.assertNotIn('"p"', log.request_body or "")


class TestHttpClient(FoodpandaTestCase):
	def test_build_path(self):
		self.assertEqual(build_path("/v2/orders/{order_token}/x", order_token="a/b"), "/v2/orders/a%2Fb/x")
		self.assertRaises(FoodpandaConfigError, build_path, "/v2/{missing}")

	def test_requires_https(self):
		account = frappe._dict(name="x", base_url="http://insecure", timeout_seconds=5, max_retries=0)
		self.assertRaises(FoodpandaConfigError, FoodpandaHttpClient, account)

	@patch("foodpanda_integration.client.http.time.sleep")
	def test_retries_on_server_error(self, sleep):
		account = frappe._dict(
			name=None, base_url="https://example.invalid", timeout_seconds=5, max_retries=2
		)
		bad = MagicMock(status_code=503, content=b"", text="", headers={})
		good = MagicMock(status_code=200, content=b"{}", text="{}", headers={})
		good.json.return_value = {"ok": True}
		session = MagicMock()
		session.request.side_effect = [bad, good]
		client = FoodpandaHttpClient(account, session=session)
		self.assertEqual(client.request("GET", "/x", operation="Test"), {"ok": True})
		self.assertEqual(session.request.call_count, 2)
		sleep.assert_called_once()

	@patch("foodpanda_integration.client.http.time.sleep")
	def test_no_retry_on_client_error(self, sleep):
		account = frappe._dict(
			name=None, base_url="https://example.invalid", timeout_seconds=5, max_retries=3
		)
		bad = MagicMock(status_code=400, content=b"", text="bad", headers={})
		session = MagicMock()
		session.request.return_value = bad
		client = FoodpandaHttpClient(account, session=session)
		self.assertRaises(FoodpandaAPIError, client.request, "GET", "/x", operation="Test")
		self.assertEqual(session.request.call_count, 1)
		sleep.assert_not_called()
