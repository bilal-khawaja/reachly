from datetime import timedelta

import jwt

import security


def test_login_ok_returns_token_with_expiry(client, user):
    r = client.post("/api/auth/login", json=user)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == security.expire_minutes() * 60
    assert security.decode_token(body["access_token"])["sub"] == user["email"]


def test_login_wrong_password(client, user):
    assert client.post("/api/auth/login", json={**user, "password": "nope"}).status_code == 401


def test_login_unknown_email(client):
    assert client.post("/api/auth/login", json={"email": "x@y.z", "password": "whatever1"}).status_code == 401


def test_protected_requires_token(client):
    assert client.get("/api/businesses").status_code == 401
    assert client.get("/api/meetings").status_code == 401


def test_garbage_token_rejected(client):
    assert client.get("/api/businesses", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_expired_token_rejected(client, user):
    token = security.create_access_token(user["email"], timedelta(seconds=-5))
    assert client.get("/api/businesses", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_signed_with_other_key_rejected(client, user):
    bad = jwt.encode({"sub": user["email"], "exp": 9999999999}, "x" * 40, algorithm="HS256")
    assert client.get("/api/businesses", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_token_for_deleted_user_rejected(client, auth):
    import db
    with db.cursor() as cur:
        cur.execute("DELETE FROM users")
    assert client.get("/api/businesses", headers=auth).status_code == 401


def test_me(client, auth):
    assert client.get("/api/auth/me", headers=auth).json()["email"] == "me@example.com"


def test_signup_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("ALLOW_SIGNUP", raising=False)
    r = client.post("/api/auth/signup", json={"email": "new@example.com", "password": "longenough1"})
    assert r.status_code == 403


def test_signup_creates_user_and_logs_in(client, monkeypatch):
    monkeypatch.setenv("ALLOW_SIGNUP", "true")
    r = client.post("/api/auth/signup", json={"email": "New@Example.com", "password": "longenough1"})
    assert r.status_code == 201
    assert security.decode_token(r.json()["access_token"])["sub"] == "new@example.com"
    assert client.post("/api/auth/login", json={"email": "new@example.com", "password": "longenough1"}).status_code == 200


def test_signup_rejects_duplicate_short_password_and_bad_email(client, user, monkeypatch):
    monkeypatch.setenv("ALLOW_SIGNUP", "true")
    assert client.post("/api/auth/signup", json=user).status_code == 409
    assert client.post("/api/auth/signup", json={"email": "a@b.co", "password": "short"}).status_code == 422
    assert client.post("/api/auth/signup", json={"email": "not-an-email", "password": "longenough1"}).status_code == 422
