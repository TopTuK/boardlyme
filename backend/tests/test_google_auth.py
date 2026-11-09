import hashlib
import hmac
from urllib.parse import urlencode

import pytest

from app.config import settings

BOT_TOKEN = "123456:TEST-BOT-TOKEN"
GOOGLE_CLAIMS = {
    "sub": "google-sub-1",
    "email": "ada@example.com",
    "given_name": "Ada",
    "family_name": "Lovelace",
    "picture": "https://example.com/ada.png",
}


@pytest.fixture
def google_settings(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr(settings, "bot_token", BOT_TOKEN)


@pytest.fixture
def mock_exchange(monkeypatch):
    """Replace the Google code exchange; tests set `.claims` (None = rejected)."""
    import app.routers.auth as auth_router

    state = {"claims": GOOGLE_CLAIMS}

    async def fake_exchange(code, redirect_uri):
        return state["claims"]

    monkeypatch.setattr(auth_router, "exchange_code", fake_exchange)
    return state


def _sign_widget(data: dict, token: str = BOT_TOKEN) -> str:
    payload = dict(data)
    secret = hashlib.sha256(token.encode()).digest()
    check = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    payload["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _google_payload() -> dict:
    return {"code": "auth-code", "redirect_uri": "http://localhost:8080/auth/signin-google"}


def test_google_login_disabled_without_config(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    assert client.post("/api/auth/google", json=_google_payload()).status_code == 503


def test_google_login_rejects_bad_code(client, google_settings, mock_exchange):
    mock_exchange["claims"] = None
    assert client.post("/api/auth/google", json=_google_payload()).status_code == 401


def test_google_login_creates_user(client, google_settings, mock_exchange):
    response = client.post("/api/auth/google", json=_google_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    user = body["user"]
    assert user["email"] == "ada@example.com"
    assert user["first_name"] == "Ada"
    assert user["telegram_id"] is None
    assert user["google_linked"] is True
    assert user["telegram_linked"] is False


def test_google_login_is_stable_across_calls(client, google_settings, mock_exchange):
    first = client.post("/api/auth/google", json=_google_payload()).json()
    second = client.post("/api/auth/google", json=_google_payload()).json()
    assert first["user"]["id"] == second["user"]["id"]


def test_link_google_to_current_account(client, google_settings, mock_exchange, make_user):
    tokens = make_user("alice")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.post("/api/auth/google/link", json=_google_payload(), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["google_linked"] is True
    assert body["telegram_linked"] is True
    assert body["email"] == "ada@example.com"


def test_link_google_conflict_when_owned_by_other_user(client, google_settings, mock_exchange, make_user):
    other = client.post("/api/auth/google", json=_google_payload()).json()
    assert other["user"]["google_linked"] is True

    tokens = make_user("alice")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.post("/api/auth/google/link", json=_google_payload(), headers=headers)
    assert response.status_code == 409


def test_link_telegram_to_current_account(client, google_settings, make_user):
    tokens = make_user("alice")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    raw = _sign_widget({"id": "4242", "first_name": "Ada", "username": "ada_tg", "auth_date": "1700000000"})
    response = client.post("/api/auth/telegram/link", json={"data": raw}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["telegram_linked"] is True
    assert body["telegram_id"] == 4242
    assert body["username"] == "ada_tg"

    # The linked Telegram identity now logs into the same account.
    login = client.post("/api/auth/telegram/widget", json={"data": raw})
    assert login.status_code == 200
    assert login.json()["user"]["id"] == tokens["user"]["id"]


def test_link_telegram_conflict_when_owned_by_other_user(client, google_settings, make_user):
    raw = _sign_widget({"id": "4242", "first_name": "Ada", "auth_date": "1700000000"})
    other = client.post("/api/auth/telegram/widget", json={"data": raw})
    assert other.status_code == 200

    tokens = make_user("alice")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.post("/api/auth/telegram/link", json={"data": raw}, headers=headers)
    assert response.status_code == 409


def test_link_telegram_rejects_bad_signature(client, google_settings, make_user):
    tokens = make_user("alice")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    raw = _sign_widget({"id": "4242", "auth_date": "1700000000"}, token="999999:WRONG")
    assert client.post("/api/auth/telegram/link", json={"data": raw}, headers=headers).status_code == 401


def test_link_endpoints_require_auth(client, google_settings):
    assert client.post("/api/auth/google/link", json=_google_payload()).status_code == 401
    assert client.post("/api/auth/telegram/link", json={"data": "id=1"}).status_code == 401
