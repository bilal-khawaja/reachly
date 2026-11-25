import os
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg2.extras import execute_values
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

import importer
from auth import current_user, router as auth_router
from db import cursor
from validators import clean_email, clean_phone, clean_website

Status = Literal["new", "contacted", "replied", "meeting_scheduled", "proposal_sent", "won", "lost"]
STATUSES = list(Status.__args__)

PROD = os.getenv("ENV", "development").lower() == "production"
DIST = Path(__file__).resolve().parent.parent / "client" / "dist"

app = FastAPI(
    title="Outreach CRM",
    docs_url=None if PROD else "/docs",
    redoc_url=None if PROD else "/redoc",
    openapi_url=None if PROD else "/openapi.json",
)
if not PROD:
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if PROD:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


@app.get("/api/health")
def health():
    with cursor() as cur:
        cur.execute("SELECT 1")
    return {"ok": True}

protected = APIRouter(dependencies=[Depends(current_user)])


def blank_to_none(v):
    return None if isinstance(v, str) and v.strip() == "" else v


class ContactChecks(BaseModel):
    """email / website: blank -> None; otherwise must match the format regex."""

    @field_validator("email", check_fields=False)
    @classmethod
    def _email(cls, v):
        return clean_email(v)

    @field_validator("website", check_fields=False)
    @classmethod
    def _website(cls, v):
        return clean_website(v)


class BusinessIn(ContactChecks):
    name: str
    phone: str
    email: Optional[str] = None
    website: Optional[str] = None
    business_type: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    channel: str = "phone"
    status: Status = "new"
    notes: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return clean_phone(v)


class BusinessPatch(ContactChecks):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    business_type: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[Status] = None
    notes: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return clean_phone(v)


class BulkDelete(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


class MeetingIn(BaseModel):
    scheduled_at: datetime
    notes: Optional[str] = None


class MeetingPatch(BaseModel):
    done: bool


@protected.get("/api/meta")
def meta():
    return {"statuses": STATUSES}


@protected.get("/api/businesses")
def list_businesses(
    user: dict = Depends(current_user),
    status: Optional[str] = None,
    city: Optional[str] = None,
    type: Optional[str] = None,
    q: Optional[str] = None,
    no_website: bool = False,
):
    where, args = ["b.user_id = %s"], [user["id"]]
    if status:
        where.append("b.status = %s"); args.append(status)
    if city:
        where.append("b.city ILIKE %s"); args.append(city)
    if type:
        where.append("b.business_type ILIKE %s"); args.append(type)
    if no_website:
        where.append("b.website IS NULL")
    if q:
        where.append("(b.name ILIKE %s OR b.phone ILIKE %s)"); args += [f"%{q}%"] * 2
    sql = f"""
        SELECT b.*,
          (SELECT min(m.scheduled_at) FROM meetings m
            WHERE m.business_id = b.id AND NOT m.done AND m.scheduled_at >= now()) AS next_meeting,
          (SELECT count(*) FROM meetings m WHERE m.business_id = b.id)::int AS meeting_count
        FROM businesses b
        WHERE {' AND '.join(where)}
        ORDER BY b.created_at DESC"""
    with cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


@protected.post("/api/businesses", status_code=201)
def create_business(body: BusinessIn, user: dict = Depends(current_user)):
    data = {k: blank_to_none(v) for k, v in body.model_dump().items()}
    if not data["name"]:
        raise HTTPException(400, "name required")
    data["user_id"] = user["id"]
    cols = list(data)
    with cursor() as cur:
        cur.execute(
            f"INSERT INTO businesses ({','.join(cols)}) VALUES ({','.join(['%s'] * len(cols))}) RETURNING *",
            [data[c] for c in cols],
        )
        return cur.fetchone()


@protected.put("/api/businesses/{bid}")
def update_business(bid: int, body: BusinessPatch, user: dict = Depends(current_user)):
    data = {k: blank_to_none(v) for k, v in body.model_dump(exclude_unset=True).items()}
    if not data:
        raise HTTPException(400, "nothing to update")
    if "name" in data and not data["name"]:
        raise HTTPException(400, "name required")
    with cursor() as cur:
        cur.execute(
            f"UPDATE businesses SET {','.join(f'{k}=%s' for k in data)}, updated_at=now() WHERE id=%s AND user_id=%s RETURNING *",
            [*data.values(), bid, user["id"]],
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "not found")
    return row


@protected.post("/api/businesses/bulk-delete")
def bulk_delete_businesses(body: BulkDelete, user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute("DELETE FROM businesses WHERE id = ANY(%s) AND user_id = %s", (body.ids, user["id"]))
        return {"deleted": cur.rowcount}


@protected.delete("/api/businesses/{bid}", status_code=204)
def delete_business(bid: int, user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute("DELETE FROM businesses WHERE id=%s AND user_id=%s", (bid, user["id"]))
    return Response(status_code=204)


@protected.get("/api/export")
def export_businesses(user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute("SELECT * FROM businesses WHERE user_id=%s ORDER BY created_at DESC", (user["id"],))
        rows = cur.fetchall()
    return Response(
        "﻿" + importer.export_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="leads-{datetime.now():%Y-%m-%d}.csv"'},
    )


def _load_import(file: UploadFile, user_id: int):
    """Parse + validate an uploaded file. Bad header -> 400; bad rows are reported, not raised."""
    try:
        _, raw_rows = importer.read_table(file.filename, file.file.read(importer.MAX_BYTES + 1))
    except importer.ImportFormatError as e:
        raise HTTPException(400, str(e))
    with cursor() as cur:
        cur.execute("SELECT lower(name) AS n, phone FROM businesses WHERE user_id=%s", (user_id,))
        seen = {(r["n"], r["phone"]) for r in cur.fetchall()}

    out = []
    for rownum, raw in raw_rows:
        raw = dict(raw)
        raw["status"] = (raw.get("status") or "new").lower().replace(" ", "_")
        raw["channel"] = (raw.get("channel") or "phone").lower()
        errors, data, duplicate = [], None, False
        if raw["channel"] not in importer.CHANNELS:
            errors.append(f"channel: must be one of {', '.join(importer.CHANNELS)}")
        try:
            data = {k: blank_to_none(v) for k, v in BusinessIn(**raw).model_dump().items()}
            if not data["name"]:
                errors.append("name: required")
        except ValidationError as e:
            errors += [f"{err['loc'][-1]}: {str(err['msg']).replace('Value error, ', '')}" for err in e.errors()]
        if data and not errors:
            key = (data["name"].lower(), data["phone"])
            duplicate = key in seen
            seen.add(key)
        out.append({"row": rownum, "data": data if not errors else raw, "errors": errors, "duplicate": duplicate})
    return out


@protected.get("/api/import/spec")
def import_spec():
    return {"columns": importer.COLUMNS, "max_rows": importer.MAX_ROWS, "max_mb": importer.MAX_BYTES // 1024 // 1024}


@protected.get("/api/import/template")
def import_template():
    return Response(
        importer.template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leads-template.csv"'},
    )


@protected.post("/api/import/preview")
def import_preview(file: UploadFile, user: dict = Depends(current_user)):
    rows = _load_import(file, user["id"])
    bad = [r for r in rows if r["errors"]]
    return {
        "total": len(rows),
        "valid": sum(1 for r in rows if not r["errors"] and not r["duplicate"]),
        "duplicates": sum(1 for r in rows if r["duplicate"]),
        "invalid": len(bad),
        "sample": [r for r in rows if not r["errors"]][:10],
        "errors": [{"row": r["row"], "messages": r["errors"]} for r in bad[:100]],
    }


@protected.post("/api/import", status_code=201)
def import_commit(file: UploadFile, user: dict = Depends(current_user)):
    """Inserts valid, non-duplicate rows; skips the rest. Re-validates server-side."""
    rows = _load_import(file, user["id"])
    good = [{**r["data"], "user_id": user["id"]} for r in rows if not r["errors"] and not r["duplicate"]]
    if good:
        cols = list(good[0])
        with cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO businesses ({','.join(cols)}) VALUES %s",
                [[d[c] for c in cols] for d in good],
            )
    return {
        "imported": len(good),
        "skipped_duplicates": sum(1 for r in rows if r["duplicate"]),
        "skipped_invalid": sum(1 for r in rows if r["errors"]),
    }


@protected.get("/api/meetings")
def list_meetings(user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute(
            "SELECT m.*, b.name AS business_name FROM meetings m "
            "JOIN businesses b ON b.id = m.business_id WHERE b.user_id = %s ORDER BY m.scheduled_at",
            (user["id"],),
        )
        return cur.fetchall()


@protected.post("/api/businesses/{bid}/meetings", status_code=201)
def add_meeting(bid: int, body: MeetingIn, user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute("SELECT 1 FROM businesses WHERE id=%s AND user_id=%s", (bid, user["id"]))
        if not cur.fetchone():
            raise HTTPException(404, "business not found")
        cur.execute(
            "INSERT INTO meetings (business_id, scheduled_at, notes) VALUES (%s,%s,%s) RETURNING *",
            (bid, body.scheduled_at, blank_to_none(body.notes)),
        )
        meeting = cur.fetchone()
        cur.execute(
            "UPDATE businesses SET status='meeting_scheduled', updated_at=now() "
            "WHERE id=%s AND status IN ('new','contacted','replied')",
            (bid,),
        )
    return meeting


@protected.patch("/api/meetings/{mid}")
def patch_meeting(mid: int, body: MeetingPatch, user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute(
            "UPDATE meetings SET done=%s WHERE id=%s AND business_id IN (SELECT id FROM businesses WHERE user_id=%s) RETURNING *",
            (body.done, mid, user["id"]),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "not found")
    return row


@protected.delete("/api/meetings/{mid}", status_code=204)
def delete_meeting(mid: int, user: dict = Depends(current_user)):
    with cursor() as cur:
        cur.execute(
            "DELETE FROM meetings WHERE id=%s AND business_id IN (SELECT id FROM businesses WHERE user_id=%s)",
            (mid, user["id"]),
        )
    return Response(status_code=204)


app.include_router(auth_router)
app.include_router(protected)


if (DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "not found")
        file = (DIST / path).resolve()
        if path and file.is_file() and DIST.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(DIST / "index.html")
