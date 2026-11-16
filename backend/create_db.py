"""Create the database named in DATABASE_URL if missing (Alembic can't do this itself)."""
import psycopg2
from sqlalchemy.engine import make_url

from db import database_url

target = make_url(database_url())
admin_url = target.set(database="postgres").render_as_string(hide_password=False)

conn = psycopg2.connect(admin_url)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target.database,))
    if cur.fetchone():
        print(f"Database {target.database} exists.")
    else:
        cur.execute('CREATE DATABASE "%s"' % target.database.replace('"', ""))
        print(f"Created database {target.database}.")
conn.close()
