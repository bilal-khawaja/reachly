import os

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from db import cursor
from security import create_access_token, decode_token, expire_minutes, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

# Checked when the email is unknown so response time doesn't reveal valid emails.
_DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeO5v4Ww4kFQx4gHk0h3b3yq1o8yQvQ8cK"


class LoginIn(BaseModel):
    email: str
    password: str


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    unauthorized = HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    try:
        email = decode_token(creds.credentials)["sub"]
    except jwt.PyJWTError:
        raise unauthorized
    with cursor() as cur:
        cur.execute("SELECT id, email FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
    if not user:
        raise unauthorized
    return user


@router.post("/login")
def login(body: LoginIn):
    with cursor() as cur:
        cur.execute("SELECT email, password_hash FROM users WHERE email = %s", (body.email.lower().strip(),))
        user = cur.fetchone()
    ok = verify_password(body.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(401, "Invalid email or password")
    return {
        "access_token": create_access_token(user["email"]),
        "token_type": "bearer",
        "expires_in": expire_minutes() * 60,
    }


@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    if os.getenv("ALLOW_SIGNUP", "false").lower() not in ("1", "true", "yes"):
        raise HTTPException(403, "Sign-up is disabled")
    email = body.email.lower().strip()
    with cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            raise HTTPException(409, "An account with this email already exists")
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, hash_password(body.password)))
    return {
        "access_token": create_access_token(email),
        "token_type": "bearer",
        "expires_in": expire_minutes() * 60,
    }


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
