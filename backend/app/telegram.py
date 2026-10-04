import hashlib
import hmac
import json
from urllib.parse import parse_qsl


def verify_telegram_query(raw: str, bot_token: str) -> dict | None:
    """Validate a Telegram-signed query string.

    Works for both the Login Widget redirect payload and the Mini App `initData`:
    both use the same HMAC-SHA256 scheme with the "WebAppData"-derived secret.

    Returns the parsed fields (without the hash) on success, None otherwise.
    """
    if not raw or not bot_token:
        return None

    data = dict(parse_qsl(raw, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        return None
    return data


def extract_telegram_user(data: dict) -> dict | None:
    """Extract the user payload from verified data.

    Mini App payloads carry a JSON-encoded `user` field; Login Widget payloads
    carry flat `id` / `first_name` / ... fields.
    """
    if "user" in data:
        try:
            user = json.loads(data["user"])
        except (TypeError, ValueError):
            return None
        return user if isinstance(user, dict) and "id" in user else None
    if "id" in data:
        return {
            "id": data["id"],
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "username": data.get("username"),
            "photo_url": data.get("photo_url"),
        }
    return None
