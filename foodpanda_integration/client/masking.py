"""Hide secrets and customer personal data before anything is written to a log.

Usage:
    from foodpanda_integration.client.masking import mask_data
    safe = mask_data({"password": "abc", "items": [...]})
"""

import json

MASK = "***"

# Any key containing one of these words (case-insensitive) is fully hidden.
SECRET_KEYS = (
	"password",
	"secret",
	"token",
	"authorization",
	"api_key",
	"apikey",
	"credential",
	"cookie",
)

# Any key containing one of these words is partly hidden (first and last characters kept),
# so staff can still recognise a record without the log exposing customer details.
PERSONAL_KEYS = (
	"phone",
	"mobile",
	"email",
	"address",
	"street",
	"building",
	"flat",
	"latitude",
	"longitude",
	"firstname",
	"first_name",
	"lastname",
	"last_name",
	"customer_name",
)

MAX_LOG_LENGTH = 20000


def _key_matches(key, words):
	key = str(key).lower().replace("-", "_")
	return any(word in key for word in words)


def mask_text(value, keep=2):
	"""'03001234567' -> '03*******67'. Short values are fully hidden."""
	text = str(value)
	if len(text) <= keep * 2 + 1:
		return MASK
	return text[:keep] + "*" * (len(text) - keep * 2) + text[-keep:]


def mask_data(data):
	"""Return a masked copy of dicts / lists / JSON strings. The original is not changed."""
	if isinstance(data, dict):
		masked = {}
		for key, value in data.items():
			if _key_matches(key, SECRET_KEYS):
				masked[key] = MASK if value not in (None, "") else value
			elif _key_matches(key, PERSONAL_KEYS) and isinstance(value, (str, int, float)):
				masked[key] = mask_text(value)
			else:
				masked[key] = mask_data(value)
		return masked
	if isinstance(data, list):
		return [mask_data(item) for item in data]
	if isinstance(data, (bytes, bytearray)):
		data = data.decode("utf-8", errors="replace")
	if isinstance(data, str):
		stripped = data.strip()
		if stripped[:1] in ("{", "["):
			try:
				return mask_data(json.loads(stripped))
			except ValueError:
				pass
		return data
	return data


def to_log_text(data):
	"""Mask, convert to pretty JSON text and cut very long bodies."""
	if data is None or data == "":
		return ""
	masked = mask_data(data)
	if isinstance(masked, (dict, list)):
		text = json.dumps(masked, indent=1, default=str, ensure_ascii=False)
	else:
		text = str(masked)
	if len(text) > MAX_LOG_LENGTH:
		text = text[:MAX_LOG_LENGTH] + "\n... (cut)"
	return text
