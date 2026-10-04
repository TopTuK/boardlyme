import hashlib
import hmac
import json
from urllib.parse import urlencode

from app.telegram import extract_telegram_user, verify_telegram_query

BOT_TOKEN = "123456:TEST-BOT-TOKEN"


def _sign(data: dict, token: str = BOT_TOKEN) -> str:
    payload = dict(data)
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    payload["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


def test_verify_valid_widget_payload():
    raw = _sign({"id": "42", "first_name": "Ada", "auth_date": "1700000000"})
    data = verify_telegram_query(raw, BOT_TOKEN)
    assert data is not None
    assert data["id"] == "42"

    user = extract_telegram_user(data)
    assert user["id"] == "42"
    assert user["first_name"] == "Ada"


def test_verify_valid_miniapp_payload():
    user_json = json.dumps({"id": 7, "first_name": "Bob", "username": "bob"})
    raw = _sign({"user": user_json, "auth_date": "1700000000", "query_id": "AAF123"})
    data = verify_telegram_query(raw, BOT_TOKEN)
    assert data is not None

    user = extract_telegram_user(data)
    assert user["id"] == 7
    assert user["username"] == "bob"


def test_rejects_tampered_payload():
    raw = _sign({"id": "42", "first_name": "Ada", "auth_date": "1700000000"})
    tampered = raw.replace("Ada", "Mallory")
    assert verify_telegram_query(tampered, BOT_TOKEN) is None


def test_rejects_wrong_bot_token():
    raw = _sign({"id": "42", "auth_date": "1700000000"})
    assert verify_telegram_query(raw, "999999:OTHER-TOKEN") is None


def test_rejects_payload_without_hash():
    assert verify_telegram_query("id=42&auth_date=1700000000", BOT_TOKEN) is None
