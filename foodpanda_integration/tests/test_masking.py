import unittest

from foodpanda_integration.client.masking import MASK, mask_data, mask_text, to_log_text


class TestMasking(unittest.TestCase):
	def test_secrets_are_hidden(self):
		data = {"username": "shop1", "password": "p@ss", "access_token": "abc", "Authorization": "Bearer x"}
		masked = mask_data(data)
		self.assertEqual(masked["username"], "shop1")
		self.assertEqual(masked["password"], MASK)
		self.assertEqual(masked["access_token"], MASK)
		self.assertEqual(masked["Authorization"], MASK)

	def test_customer_data_is_partly_hidden(self):
		masked = mask_data({"customer": {"mobilePhone": "03001234567", "email": "ali@example.com"}})
		self.assertEqual(masked["customer"]["mobilePhone"], "03*******67")
		self.assertNotIn("ali@example", masked["customer"]["email"])

	def test_nested_lists_and_json_strings(self):
		masked = mask_data('{"items": [{"name": "Burger", "secret": "s"}]}')
		self.assertEqual(masked["items"][0]["name"], "Burger")
		self.assertEqual(masked["items"][0]["secret"], MASK)

	def test_original_is_not_changed(self):
		data = {"password": "keep"}
		mask_data(data)
		self.assertEqual(data["password"], "keep")

	def test_short_values_fully_hidden(self):
		self.assertEqual(mask_text("123"), MASK)

	def test_log_text_is_cut(self):
		text = to_log_text({"blob": "x" * 50000})
		self.assertTrue(text.endswith("(cut)"))
