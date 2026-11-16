def mk(client, auth, **kw):
    body = {"name": "Acme Plumbing", "phone": "506-555-0100", "city": "Moncton", "business_type": "plumbing", **kw}
    r = client.post("/api/businesses", json=body, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_list(client, auth):
    b = mk(client, auth)
    assert b["status"] == "new" and b["channel"] == "phone"
    rows = client.get("/api/businesses", headers=auth).json()
    assert [r["name"] for r in rows] == ["Acme Plumbing"]
    assert rows[0]["meeting_count"] == 0 and rows[0]["next_meeting"] is None


def test_blank_strings_become_null(client, auth):
    b = mk(client, auth, email="", website="  ")
    assert b["email"] is None and b["website"] is None


def test_create_requires_name(client, auth):
    assert client.post("/api/businesses", json={"name": " ", "phone": "1"}, headers=auth).status_code == 400
    assert client.post("/api/businesses", json={}, headers=auth).status_code == 422


def test_invalid_status_rejected(client, auth):
    assert client.post("/api/businesses", json={"name": "A", "phone": "1", "status": "bogus"}, headers=auth).status_code == 422


def test_update_partial(client, auth):
    b = mk(client, auth)
    r = client.put(f"/api/businesses/{b['id']}", json={"status": "contacted"}, headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "contacted" and r.json()["name"] == "Acme Plumbing"
    assert client.put("/api/businesses/9999", json={"city": "X"}, headers=auth).status_code == 404
    assert client.put(f"/api/businesses/{b['id']}", json={}, headers=auth).status_code == 400
    assert client.put(f"/api/businesses/{b['id']}", json={"bogus": 1}, headers=auth).status_code == 422


def test_filters(client, auth):
    mk(client, auth, name="A", city="Moncton", business_type="hvac")
    mk(client, auth, name="B", city="Sudbury", business_type="dental", status="contacted")
    get = lambda **p: [r["name"] for r in client.get("/api/businesses", params=p, headers=auth).json()]
    assert get(city="moncton") == ["A"]
    assert get(type="dental") == ["B"]
    assert get(status="contacted") == ["B"]
    assert get(q="b") == ["B"]


def test_meeting_flow(client, auth):
    b = mk(client, auth)
    r = client.post(f"/api/businesses/{b['id']}/meetings",
                    json={"scheduled_at": "2099-01-01T15:00:00Z", "notes": "intro call"}, headers=auth)
    assert r.status_code == 201
    mid = r.json()["id"]
    row = client.get("/api/businesses", headers=auth).json()[0]
    assert row["status"] == "meeting_scheduled" and row["meeting_count"] == 1 and row["next_meeting"]

    assert client.get("/api/meetings", headers=auth).json()[0]["business_name"] == "Acme Plumbing"
    assert client.patch(f"/api/meetings/{mid}", json={"done": True}, headers=auth).json()["done"] is True
    assert client.get("/api/businesses", headers=auth).json()[0]["next_meeting"] is None
    assert client.delete(f"/api/meetings/{mid}", headers=auth).status_code == 204


def test_meeting_does_not_downgrade_later_status(client, auth):
    b = mk(client, auth, status="won")
    client.post(f"/api/businesses/{b['id']}/meetings", json={"scheduled_at": "2099-01-01T15:00:00Z"}, headers=auth)
    assert client.get("/api/businesses", headers=auth).json()[0]["status"] == "won"


def test_meeting_for_missing_business(client, auth):
    r = client.post("/api/businesses/999/meetings", json={"scheduled_at": "2099-01-01T15:00:00Z"}, headers=auth)
    assert r.status_code == 404


def test_delete_business_cascades_meetings(client, auth):
    b = mk(client, auth)
    client.post(f"/api/businesses/{b['id']}/meetings", json={"scheduled_at": "2099-01-01T15:00:00Z"}, headers=auth)
    assert client.delete(f"/api/businesses/{b['id']}", headers=auth).status_code == 204
    assert client.get("/api/meetings", headers=auth).json() == []


def test_bulk_delete(client, auth):
    a, b, c = (mk(client, auth, name=n)["id"] for n in "ABC")
    client.post(f"/api/businesses/{a}/meetings", json={"scheduled_at": "2099-01-01T15:00:00Z"}, headers=auth)
    r = client.post("/api/businesses/bulk-delete", json={"ids": [a, b, 9999]}, headers=auth)
    assert r.status_code == 200 and r.json() == {"deleted": 2}
    assert [x["name"] for x in client.get("/api/businesses", headers=auth).json()] == ["C"]
    assert client.get("/api/meetings", headers=auth).json() == []


def test_bulk_delete_validation_and_auth(client, auth):
    assert client.post("/api/businesses/bulk-delete", json={"ids": []}, headers=auth).status_code == 422
    assert client.post("/api/businesses/bulk-delete", json={"ids": [1]}).status_code == 401
