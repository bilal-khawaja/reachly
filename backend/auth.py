import os
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from db import cursor
import ratelimit
from invites import hash_token
from security import create_access_token, decode_token, expire_minutes, hash_password, session_max_days, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

COOKIE = "crm_session"


def set_session(resp: Response, email: str, ver: int = 0, auth_time: datetime | None = None) -> dict:
    """Session token lives only in an httpOnly cookie: page JavaScript (and so any XSS) can't read it."""
    resp.set_cookie(
        COOKIE,
        create_access_token(email, ver=ver, auth_time=auth_time),
        max_age=expire_minutes() * 60,
        httponly=True,
        secure=os.getenv("ENV", "development").lower() == "production",
        samesite="lax",
        path="/",
    )
    return {"ok": True, "expires_in": expire_minutes() * 60}


_DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeO5v4Ww4kFQx4gHk0h3b3yq1o8yQvQ8cK"


class LoginIn(BaseModel):
    email: str
    password: str


class SignupIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)


def current_user(
    request: Request, response: Response, creds: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> dict:
    """Valid while: signature + expiry ok, token_version matches, and the real login is within SESSION_MAX_DAYS.
    A cookie past half its life is re-issued (sliding session), so active users stay logged in."""
    unauthorized = HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    cookie = request.cookies.get(COOKIE)
    token = cookie or (creds.credentials if creds else None)
    if not token:
        raise unauthorized
    try:
        claims = decode_token(token)
        email, ver, auth_ts = claims["sub"], claims["ver"], claims["auth"]
    except (jwt.PyJWTError, KeyError):
        raise unauthorized
    with cursor() as cur:
        cur.execute("SELECT id, email, token_version FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
    if not row or row["token_version"] != ver:
        raise unauthorized
    now = datetime.now(timezone.utc).timestamp()
    if now - auth_ts > session_max_days() * 86400:
        raise unauthorized
    if cookie and claims["exp"] - now < expire_minutes() * 30:
        set_session(response, email, ver, datetime.fromtimestamp(auth_ts, timezone.utc))
    return {"id": row["id"], "email": row["email"]}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    ip = ratelimit.client_ip(request)
    ratelimit.check(ip)
    with cursor() as cur:
        cur.execute("SELECT email, password_hash, token_version FROM users WHERE email = %s", (body.email.lower().strip(),))
        user = cur.fetchone()
    ok = verify_password(body.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok:
        ratelimit.record_failure(ip)
        raise HTTPException(401, "Invalid email or password")
    ratelimit.reset(ip)
    return set_session(response, user["email"], user["token_version"])


@router.get("/invite/{token}")
def invite_info(token: str):
    """Lets the sign-up page show which email an invite is for. Same 404 for unknown, used and expired."""
    with cursor() as cur:
        cur.execute(
            "SELECT email FROM invites WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()",
            (hash_token(token),),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "This invite link is invalid or has expired")
    return {"email": row["email"]}


@router.post("/signup", status_code=201)
def signup(body: SignupIn, response: Response):
    """Invite-only: the token is single use and fixes the email."""
    with cursor() as cur:
        cur.execute(
            "UPDATE invites SET used_at = now() WHERE token_hash = %s AND used_at IS NULL AND expires_at > now() "
            "RETURNING email",
            (hash_token(body.token),),
        )
        invite = cur.fetchone()
        if not invite:
            raise HTTPException(403, "This invite link is invalid or has expired")
        email = invite["email"]
        cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            raise HTTPException(409, "An account with this email already exists")
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, hash_password(body.password)))
    return set_session(response, email)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")


@router.post("/logout-all", status_code=204)
def logout_all(response: Response, user: dict = Depends(current_user)):
    """Invalidates every session of this user on every device."""
    with cursor() as cur:
        cur.execute("UPDATE users SET token_version = token_version + 1 WHERE id = %s", (user["id"],))
    response.delete_cookie(COOKIE, path="/")


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
