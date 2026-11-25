"""Invite tokens. Only a SHA-256 hash is stored; the raw token exists only in the link given to the invitee."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

INVITE_DAYS = 7


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_invite(cur, email: str, days: int = INVITE_DAYS) -> str:
    """Returns the raw token. Older unused invites for the same email are revoked."""
    token = secrets.token_urlsafe(32)
    cur.execute("DELETE FROM invites WHERE email = %s AND used_at IS NULL", (email,))
    cur.execute(
        "INSERT INTO invites (email, token_hash, expires_at) VALUES (%s, %s, %s)",
        (email, hash_token(token), datetime.now(timezone.utc) + timedelta(days=days)),
    )
    return token
