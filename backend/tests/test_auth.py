from app.config import settings


def test_dev_login_returns_tokens_and_user(client):
    response = client.post("/api/auth/dev-login", json={"username": "alice"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["username"] == "alice"


def test_dev_login_is_stable_across_calls(client):
    first = client.post("/api/auth/dev-login", json={"username": "alice"}).json()
    second = client.post("/api/auth/dev-login", json={"username": "alice"}).json()
    assert first["user"]["id"] == second["user"]["id"]


def test_dev_login_disabled_in_production_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "dev_fake_auth", False)
    assert client.post("/api/auth/dev-login", json={"username": "alice"}).status_code == 404


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_valid_token(client, make_user):
    tokens = make_user("alice")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == tokens["user"]["id"]
    assert body["locale"] == "en"


def test_update_locale(client, make_user):
    tokens = make_user("alice")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.patch("/api/auth/me", json={"locale": "ru"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["locale"] == "ru"
    assert client.get("/api/auth/me", headers=headers).json()["locale"] == "ru"
    assert client.patch("/api/auth/me", json={"locale": "de"}, headers=headers).status_code == 422


def test_me_rejects_garbage_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_refresh_token_exchange(client, make_user):
    tokens = make_user("alice")
    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_refresh_rejects_access_token(client, make_user):
    tokens = make_user("alice")
    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_refresh_rejects_garbage(client):
    assert client.post("/api/auth/refresh", json={"refresh_token": "garbage"}).status_code == 401


def test_meta_endpoint(client):
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "Boardly"
    assert body["dev_fake_auth"] is True
