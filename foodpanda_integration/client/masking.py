"""Hide secrets and customer personal data before anything is written to a log.

Usage:
    from foodpanda_integration.client.masking import mask_data
    safe = mask_data({"password": "abc", "items": [...]})
"""

import json
import re
from urllib.parse import parse_qsl, urlencode

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
	"full_name",
	"recipient",
)

MAX_LOG_LENGTH = 20000


_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
# key=value or "key": "value" pairs inside free text (URLs, error messages, form bodies)
_PAIR = re.compile(r"([A-Za-z_][A-Za-z0-9_\-]*)(=|\"?\s*:\s*\"?)([^&\s\",}?=]+)")


def _normalise_key(key):
	"""'customerName' / 'Customer-Name' -> 'customer_name'."""
	return _CAMEL.sub("_", str(key)).lower().replace("-", "_")


def _key_matches(key, words):
	key = _normalise_key(key)
	compact = key.replace("_", "")
	return any(word in key or word.replace("_", "") in compact for word in words)


def mask_free_text(text):
	"""Hide secret / personal values that appear as key=value or "key": "value" in plain text."""
	if not text:
		return text

	def replace(match):
		key, sep, value = match.groups()
		if _key_matches(key, SECRET_KEYS):
			return f"{key}{sep}{MASK}"
		if _key_matches(key, PERSONAL_KEYS):
			return f"{key}{sep}{mask_text(value)}"
		return match.group(0)

	text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+", r"\1" + MASK, str(text))
	return _PAIR.sub(replace, text)


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
		if "=" in stripped and " " not in stripped:  # form-encoded body: a=1&b=2
			pairs = parse_qsl(stripped, keep_blank_values=True)
			if pairs:
				return urlencode(list(mask_data(dict(pairs)).items()), safe="*")
		return mask_free_text(data)
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
