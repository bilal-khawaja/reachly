from datetime import timedelta

import jwt

import security


def test_login_ok_returns_token_with_expiry(client, user):
    r = client.post("/api/auth/login", json=user)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "expires_in": security.expire_minutes() * 60}
    assert "access_token" not in r.text
    assert security.decode_token(r.cookies["crm_session"])["sub"] == user["email"]
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


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


def _invite(email="new@example.com"):
    import db, invites
    with db.cursor() as cur:
        return invites.create_invite(cur, email)


def test_signup_requires_valid_invite(client):
    assert client.post("/api/auth/signup", json={"token": "x" * 20, "password": "longenough1"}).status_code == 403
    assert client.get("/api/auth/invite/" + "x" * 20).status_code == 404


def test_signup_with_invite_creates_user_and_logs_in(client):
    tok = _invite()
    assert client.get(f"/api/auth/invite/{tok}").json() == {"email": "new@example.com"}
    r = client.post("/api/auth/signup", json={"token": tok, "password": "longenough1"})
    assert r.status_code == 201
    assert security.decode_token(r.cookies["crm_session"])["sub"] == "new@example.com"
    assert client.post("/api/auth/login", json={"email": "new@example.com", "password": "longenough1"}).status_code == 200


def test_invite_is_single_use(client):
    tok = _invite()
    assert client.post("/api/auth/signup", json={"token": tok, "password": "longenough1"}).status_code == 201
    assert client.post("/api/auth/signup", json={"token": tok, "password": "another-pass1"}).status_code == 403
    assert client.get(f"/api/auth/invite/{tok}").status_code == 404


def test_expired_invite_rejected(client):
    import db
    tok = _invite()
    with db.cursor() as cur:
        cur.execute("UPDATE invites SET expires_at = now() - interval '1 minute'")
    assert client.post("/api/auth/signup", json={"token": tok, "password": "longenough1"}).status_code == 403


def test_new_invite_revokes_old_one_and_short_password_keeps_invite_usable(client):
    old = _invite()
    new = _invite()
    assert client.post("/api/auth/signup", json={"token": old, "password": "longenough1"}).status_code == 403
    assert client.post("/api/auth/signup", json={"token": new, "password": "short"}).status_code == 422
    assert client.post("/api/auth/signup", json={"token": new, "password": "longenough1"}).status_code == 201


def test_invite_for_existing_user_conflicts_and_is_not_consumed_silently(client, user):
    tok = _invite(user["email"])
    assert client.post("/api/auth/signup", json={"token": tok, "password": "longenough1"}).status_code == 409


def test_cookie_session_works_and_logout_clears_it(client, user):
    client.post("/api/auth/login", json=user)
    assert client.get("/api/auth/me").json()["email"] == user["email"]
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_cookie_is_secure_in_production(client, user, monkeypatch):
    monkeypatch.setenv("ENV", "production")
    assert "secure" in client.post("/api/auth/login", json=user).headers["set-cookie"].lower()


def _cookie_for(email, minutes, auth_age_days=0, ver=0):
    from datetime import datetime, timedelta, timezone
    return security.create_access_token(
        email, timedelta(minutes=minutes), ver=ver, auth_time=datetime.now(timezone.utc) - timedelta(days=auth_age_days)
    )


def test_fresh_session_is_not_reissued(client, user):
    r = client.post("/api/auth/login", json=user)
    assert "set-cookie" not in client.get("/api/auth/me").headers


def test_session_slides_when_past_half_life(client, user):
    client.cookies.set("crm_session", _cookie_for(user["email"], minutes=10))
    r = client.get("/api/auth/me")
    assert r.status_code == 200 and "crm_session=" in r.headers["set-cookie"]
    assert security.decode_token(r.cookies["crm_session"])["exp"] > security.decode_token(_cookie_for(user["email"], 10))["exp"]


def test_renewal_keeps_original_login_time(client, user):
    old = _cookie_for(user["email"], minutes=10, auth_age_days=2)
    client.cookies.set("crm_session", old)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert security.decode_token(r.cookies["crm_session"])["auth"] == security.decode_token(old)["auth"]


def test_absolute_session_cap(client, user):
    client.cookies.set("crm_session", _cookie_for(user["email"], minutes=59, auth_age_days=8))
    assert client.get("/api/auth/me").status_code == 401


def test_token_without_version_claim_rejected(client, user):
    import jwt as pyjwt
    bad = pyjwt.encode({"sub": user["email"], "exp": 9999999999}, security._secret(), algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_logout_all_invalidates_every_session(client, user):
    a = client.post("/api/auth/login", json=user).cookies["crm_session"]
    b = client.post("/api/auth/login", json=user).cookies["crm_session"]
    client.cookies.clear()
    assert client.post("/api/auth/logout-all", headers={"Authorization": f"Bearer {a}"}).status_code == 204
    for t in (a, b):
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"}).status_code == 401
    assert client.post("/api/auth/login", json=user).status_code == 200
