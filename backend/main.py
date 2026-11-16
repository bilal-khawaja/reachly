from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from auth import current_user, router as auth_router
from db import cursor
from validators import clean_email, clean_phone, clean_website

Status = Literal["new", "contacted", "replied", "meeting_scheduled", "proposal_sent", "won", "lost"]
STATUSES = list(Status.__args__)

app = FastAPI(title="Outreach CRM")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

# Everything except /api/auth/login requires a valid bearer token.
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
        return clean_phone(v)  # explicit null / blank is rejected; omit the field to leave it unchanged


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
    status: Optional[str] = None,
    city: Optional[str] = None,
    type: Optional[str] = None,
    q: Optional[str] = None,
    no_website: bool = False,
):
    where, args = [], []
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
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY b.created_at DESC"""
    with cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


@protected.post("/api/businesses", status_code=201)
def create_business(body: BusinessIn):
    data = {k: blank_to_none(v) for k, v in body.model_dump().items()}
    if not data["name"]:
        raise HTTPException(400, "name required")
    cols = list(data)
    with cursor() as cur:
        cur.execute(
            f"INSERT INTO businesses ({','.join(cols)}) VALUES ({','.join(['%s'] * len(cols))}) RETURNING *",
            [data[c] for c in cols],
        )
        return cur.fetchone()


@protected.put("/api/businesses/{bid}")
def update_business(bid: int, body: BusinessPatch):
    data = {k: blank_to_none(v) for k, v in body.model_dump(exclude_unset=True).items()}
    if not data:
        raise HTTPException(400, "nothing to update")
    if "name" in data and not data["name"]:
        raise HTTPException(400, "name required")
    with cursor() as cur:
        cur.execute(
            f"UPDATE businesses SET {','.join(f'{k}=%s' for k in data)}, updated_at=now() WHERE id=%s RETURNING *",
            [*data.values(), bid],
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "not found")
    return row


@protected.post("/api/businesses/bulk-delete")
def bulk_delete_businesses(body: BulkDelete):
    with cursor() as cur:
        cur.execute("DELETE FROM businesses WHERE id = ANY(%s)", (body.ids,))
        return {"deleted": cur.rowcount}


@protected.delete("/api/businesses/{bid}", status_code=204)
def delete_business(bid: int):
    with cursor() as cur:
        cur.execute("DELETE FROM businesses WHERE id=%s", (bid,))
    return Response(status_code=204)


@protected.get("/api/meetings")
def list_meetings():
    with cursor() as cur:
        cur.execute(
            "SELECT m.*, b.name AS business_name FROM meetings m "
            "JOIN businesses b ON b.id = m.business_id ORDER BY m.scheduled_at"
        )
        return cur.fetchall()


@protected.post("/api/businesses/{bid}/meetings", status_code=201)
def add_meeting(bid: int, body: MeetingIn):
    with cursor() as cur:
        cur.execute("SELECT 1 FROM businesses WHERE id=%s", (bid,))
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
def patch_meeting(mid: int, body: MeetingPatch):
    with cursor() as cur:
        cur.execute("UPDATE meetings SET done=%s WHERE id=%s RETURNING *", (body.done, mid))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "not found")
    return row


@protected.delete("/api/meetings/{mid}", status_code=204)
def delete_meeting(mid: int):
    with cursor() as cur:
        cur.execute("DELETE FROM meetings WHERE id=%s", (mid,))
    return Response(status_code=204)


app.include_router(auth_router)
app.include_router(protected)
