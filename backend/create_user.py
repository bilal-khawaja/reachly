"""Create or update a user: python backend/create_user.py EMAIL [PASSWORD]  (prompts if no password)."""
import getpass
import sys

from db import cursor
from security import hash_password

if len(sys.argv) < 2:
    sys.exit("usage: create_user.py EMAIL [PASSWORD]")
email = sys.argv[1].lower().strip()
password = sys.argv[2] if len(sys.argv) > 2 else getpass.getpass("Password: ")
if len(password) < 8:
    sys.exit("password must be at least 8 characters")

with cursor() as cur:
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s) "
        "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash",
        (email, hash_password(password)),
    )
print(f"User {email} saved.")
