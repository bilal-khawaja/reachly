import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Point everything at a dedicated test DB before app modules are imported.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from sqlalchemy.engine import make_url  # noqa: E402

_real = make_url(os.environ["DATABASE_URL"])
TEST_DB = f"{_real.database}_test"
os.environ["DATABASE_URL"] = _real.set(database=TEST_DB).render_as_string(hide_password=False)

import psycopg2  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
import security  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_database():
    admin = psycopg2.connect(_real.set(database="postgres").render_as_string(hide_password=False))
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (TEST_DB,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    admin.close()
    subprocess.run(["alembic", "upgrade", "head"], cwd=ROOT, check=True, env=os.environ.copy())
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    with db.cursor() as cur:
        cur.execute("TRUNCATE meetings, businesses, users RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user():
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            ("me@example.com", security.hash_password("correct-horse")),
        )
    return {"email": "me@example.com", "password": "correct-horse"}


@pytest.fixture
def auth(client, user):
    r = client.post("/api/auth/login", json=user)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
