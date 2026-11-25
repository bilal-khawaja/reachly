"""User A must never see or touch user B's leads."""
import io

import pytest

import db
import security

LATER = {"scheduled_at": "2099-01-01T15:00:00Z"}


@pytest.fixture
def other(client):
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            ("other@example.com", security.hash_password("battery-staple")),
        )
    r = client.post("/api/auth/login", json={"email": "other@example.com", "password": "battery-staple"})
    client.cookies.clear()
    return {"Authorization": f"Bearer {r.cookies['crm_session']}"}


@pytest.fixture
def mine(client, auth):
    b = client.post("/api/businesses", json={"name": "Acme", "phone": "555"}, headers=auth).json()
    m = client.post(f"/api/businesses/{b['id']}/meetings", json=LATER, headers=auth).json()
    return b, m


def test_list_and_export_are_scoped(client, auth, other, mine):
    assert client.get("/api/businesses", headers=other).json() == []
    assert client.get("/api/meetings", headers=other).json() == []
    assert "Acme" not in client.get("/api/export", headers=other).text
    assert len(client.get("/api/businesses", headers=auth).json()) == 1


def test_cannot_modify_others_business(client, auth, other, mine):
    b, _ = mine
    assert client.put(f"/api/businesses/{b['id']}", json={"city": "X"}, headers=other).status_code == 404
    client.delete(f"/api/businesses/{b['id']}", headers=other)
    assert client.post("/api/businesses/bulk-delete", json={"ids": [b["id"]]}, headers=other).json()["deleted"] == 0
    row = client.get("/api/businesses", headers=auth).json()[0]
    assert row["name"] == "Acme" and row["city"] is None


def test_cannot_touch_others_meetings(client, auth, other, mine):
    b, m = mine
    assert client.post(f"/api/businesses/{b['id']}/meetings", json=LATER, headers=other).status_code == 404
    assert client.patch(f"/api/meetings/{m['id']}", json={"done": True}, headers=other).status_code == 404
    client.delete(f"/api/meetings/{m['id']}", headers=other)
    ms = client.get("/api/meetings", headers=auth).json()
    assert len(ms) == 1 and ms[0]["done"] is False


def test_import_dedupe_is_per_user(client, auth, other, mine):
    csv = b"name,phone\nAcme,555\n"
    files = lambda: {"file": ("l.csv", io.BytesIO(csv), "text/csv")}
    assert client.post("/api/import", files=files(), headers=auth).json()["skipped_duplicates"] == 1
    assert client.post("/api/import", files=files(), headers=other).json()["imported"] == 1
    assert len(client.get("/api/businesses", headers=other).json()) == 1


def test_login_rate_limited_after_repeated_failures(client, user):
    bad = {**user, "password": "wrong-pass"}
    assert [client.post("/api/auth/login", json=bad).status_code for _ in range(5)] == [401] * 5
    r = client.post("/api/auth/login", json=user)
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_health_and_security_headers(client):
    r = client.get("/api/health")
    assert r.json() == {"ok": True}
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
