import psycopg2
import pytest

import db
from validators import EMAIL_PG, EMAIL_RE, WEBSITE_PG, WEBSITE_RE

GOOD_EMAILS = ["a@b.co", "first.last+tag@sub.example.com", "X_Y%z@ex-ample.ca"]
BAD_EMAILS = ["plain", "a@b", "a@@b.co", "a b@c.co", "@b.co", "a@.co", "a@b.c"]
GOOD_SITES = ["example.com", "http://example.com", "https://www.ex-ample.ca/path?q=1", "shop.example.co.uk:8080/x"]
BAD_SITES = ["example", "http://", "ht tp://a.com", "just words", "http://a.c", "a..com"]


def mk(client, auth, **kw):
    return client.post("/api/businesses", json={"name": "Co", "phone": "506-555-0100", **kw}, headers=auth)


def test_email_website_default_to_none(client, auth):
    r = mk(client, auth)
    assert r.status_code == 201
    assert r.json()["email"] is None and r.json()["website"] is None


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_becomes_none(client, auth, blank):
    r = mk(client, auth, email=blank, website=blank)
    assert r.status_code == 201 and r.json()["email"] is None and r.json()["website"] is None


@pytest.mark.parametrize("email", GOOD_EMAILS)
def test_valid_email_accepted_and_lowercased(client, auth, email):
    r = mk(client, auth, email=email)
    assert r.status_code == 201 and r.json()["email"] == email.lower()


@pytest.mark.parametrize("email", BAD_EMAILS)
def test_invalid_email_rejected(client, auth, email):
    assert mk(client, auth, email=email).status_code == 422


@pytest.mark.parametrize("site", GOOD_SITES)
def test_valid_website_accepted(client, auth, site):
    r = mk(client, auth, website=site)
    assert r.status_code == 201 and r.json()["website"] == site


@pytest.mark.parametrize("site", BAD_SITES)
def test_invalid_website_rejected(client, auth, site):
    assert mk(client, auth, website=site).status_code == 422


def test_update_validates_and_can_clear(client, auth):
    bid = mk(client, auth, email="a@b.co", website="example.com").json()["id"]
    assert client.put(f"/api/businesses/{bid}", json={"email": "nope"}, headers=auth).status_code == 422
    r = client.put(f"/api/businesses/{bid}", json={"email": "", "website": ""}, headers=auth)
    assert r.status_code == 200 and r.json()["email"] is None and r.json()["website"] is None


@pytest.mark.parametrize("col,val", [("email", "not-an-email"), ("website", "not a site")])
def test_database_rejects_bad_values_directly(col, val):
    with pytest.raises(psycopg2.errors.CheckViolation):
        with db.cursor() as cur:
            cur.execute(f"INSERT INTO businesses (name, phone, {col}) VALUES ('x', '1', %s)", (val,))


def test_python_and_postgres_regex_agree():
    with db.cursor() as cur:
        for v in GOOD_EMAILS + BAD_EMAILS:
            cur.execute("SELECT %s ~ %s AS m", (v, EMAIL_PG))
            assert cur.fetchone()["m"] == bool(EMAIL_RE.match(v)), v
        for v in GOOD_SITES + BAD_SITES:
            cur.execute("SELECT %s ~ %s AS m", (v, WEBSITE_PG))
            assert cur.fetchone()["m"] == bool(WEBSITE_RE.match(v)), v


def test_phone_required(client, auth):
    assert client.post("/api/businesses", json={"name": "Co"}, headers=auth).status_code == 422
    for blank in ("", "   ", None):
        assert client.post("/api/businesses", json={"name": "Co", "phone": blank}, headers=auth).status_code == 422


def test_phone_trimmed_and_update_cannot_blank_it(client, auth):
    bid = mk(client, auth, phone="  506 555 0100 ").json()
    assert bid["phone"] == "506 555 0100"
    for blank in ("", None):
        assert client.put(f"/api/businesses/{bid['id']}", json={"phone": blank}, headers=auth).status_code == 422
    assert client.put(f"/api/businesses/{bid['id']}", json={"city": "X"}, headers=auth).status_code == 200  # omitted = unchanged
    assert client.put(f"/api/businesses/{bid['id']}", json={"phone": "999"}, headers=auth).json()["phone"] == "999"


@pytest.mark.parametrize("phone", [None, "   "])
def test_database_rejects_missing_phone(phone):
    with pytest.raises(psycopg2.Error):
        with db.cursor() as cur:
            cur.execute("INSERT INTO businesses (name, phone) VALUES ('x', %s)", (phone,))


def test_no_website_filter(client, auth):
    mk(client, auth, name="Has site", website="example.com")
    mk(client, auth, name="No site")
    names = lambda **p: sorted(r["name"] for r in client.get("/api/businesses", params=p, headers=auth).json())
    assert names() == ["Has site", "No site"]
    assert names(no_website="true") == ["No site"]
