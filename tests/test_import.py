import io

from openpyxl import Workbook

CSV_OK = (
    "name,phone,email,website,status\n"
    "Acme Plumbing,506-555-0100,INFO@acme.com,acme.com,Contacted\n"
    "Bright Dental,506-555-0101,,,\n"
)


def up(client, auth, content, name="leads.csv", path="/api/import"):
    if isinstance(content, str):
        content = content.encode()
    return client.post(path, files={"file": (name, content)}, headers=auth)


def xlsx_bytes(rows):
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_requires_auth(client):
    assert client.post("/api/import", files={"file": ("a.csv", b"x")}).status_code == 401
    assert client.get("/api/import/template").status_code == 401


def test_spec_and_template(client, auth):
    spec = client.get("/api/import/spec", headers=auth).json()
    assert [c["name"] for c in spec["columns"]][:2] == ["name", "phone"]
    t = client.get("/api/import/template", headers=auth)
    assert t.headers["content-type"].startswith("text/csv")
    assert t.text.splitlines()[0].startswith("name,phone")
    # template must itself import cleanly
    assert up(client, auth, t.text, path="/api/import/preview").json()["invalid"] == 0


def test_csv_import(client, auth):
    r = up(client, auth, CSV_OK)
    assert r.status_code == 201 and r.json() == {"imported": 2, "skipped_duplicates": 0, "skipped_invalid": 0}
    rows = {b["name"]: b for b in client.get("/api/businesses", headers=auth).json()}
    assert rows["Acme Plumbing"]["email"] == "info@acme.com"
    assert rows["Acme Plumbing"]["status"] == "contacted"
    assert rows["Bright Dental"]["status"] == "new" and rows["Bright Dental"]["channel"] == "phone"


def test_extra_column_rejected(client, auth):
    r = up(client, auth, "name,phone,bogus\nA,1,x\n")
    assert r.status_code == 400 and "bogus" in r.json()["detail"]
    assert client.get("/api/businesses", headers=auth).json() == []


def test_missing_required_column_rejected(client, auth):
    r = up(client, auth, "name,city\nA,X\n")
    assert r.status_code == 400 and "phone" in r.json()["detail"]


def test_duplicate_header_rejected(client, auth):
    assert up(client, auth, "name,phone,phone\nA,1,2\n").status_code == 400


def test_header_case_and_spaces_normalised(client, auth):
    r = up(client, auth, "Name, Phone ,Business Type\nA,1,hvac\n")
    assert r.status_code == 201
    assert client.get("/api/businesses", headers=auth).json()[0]["business_type"] == "hvac"


def test_bad_rows_skipped_and_reported(client, auth):
    body = "name,phone,email,channel\nGood,1,,\n,2,,\nBadMail,3,nope,\nBadChan,4,,carrier pigeon\nNoPhone,,,\n"
    p = up(client, auth, body, path="/api/import/preview").json()
    assert (p["total"], p["valid"], p["invalid"]) == (5, 1, 4)
    assert {e["row"] for e in p["errors"]} == {3, 4, 5, 6}
    r = up(client, auth, body).json()
    assert r["imported"] == 1 and r["skipped_invalid"] == 4
    assert len(client.get("/api/businesses", headers=auth).json()) == 1


def test_duplicates_skipped(client, auth):
    up(client, auth, CSV_OK)
    r = up(client, auth, CSV_OK + "acme plumbing,506-555-0100\n").json()
    assert r == {"imported": 0, "skipped_duplicates": 3, "skipped_invalid": 0}


def test_preview_does_not_write(client, auth):
    assert up(client, auth, CSV_OK, path="/api/import/preview").json()["valid"] == 2
    assert client.get("/api/businesses", headers=auth).json() == []


def test_xlsx_import_numeric_phone(client, auth):
    data = xlsx_bytes([["name", "phone", None], ["Acme", 5065550100, None], [None, None, None], ["Beta", "0123", None]])
    r = up(client, auth, data, name="leads.xlsx")
    assert r.status_code == 201 and r.json()["imported"] == 2
    phones = {b["name"]: b["phone"] for b in client.get("/api/businesses", headers=auth).json()}
    assert phones == {"Acme": "5065550100", "Beta": "0123"}


def test_bad_file_types(client, auth):
    assert up(client, auth, "x", name="a.txt").status_code == 400
    assert up(client, auth, b"not a workbook", name="a.xlsx").status_code == 400
    assert up(client, auth, "", name="a.csv").status_code == 400
    assert up(client, auth, "name,phone\n", name="a.csv").status_code == 400
