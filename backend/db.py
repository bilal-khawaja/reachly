import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy.engine import make_url

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def database_url() -> str:
    """DATABASE_URL, normalized to a libpq-compatible postgresql:// URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


_pool: ThreadedConnectionPool | None = None


def pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(1, 10, database_url(), cursor_factory=RealDictCursor)
    return _pool


@contextmanager
def cursor():
    p = pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)
