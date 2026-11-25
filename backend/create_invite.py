"""Invite someone: python backend/create_invite.py EMAIL [DAYS]. Prints a one-time sign-up link to send them."""
import os
import sys

from db import cursor
from invites import INVITE_DAYS, create_invite

if len(sys.argv) < 2:
    sys.exit("usage: create_invite.py EMAIL [DAYS]")
email = sys.argv[1].lower().strip()
days = int(sys.argv[2]) if len(sys.argv) > 2 else INVITE_DAYS

with cursor() as cur:
    cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        sys.exit(f"{email} already has an account")
    token = create_invite(cur, email, days)

base = os.getenv("APP_URL", "http://localhost:5173").rstrip("/")
print(f"Invite for {email} (valid {days} days, single use):\n{base}/?invite={token}")
