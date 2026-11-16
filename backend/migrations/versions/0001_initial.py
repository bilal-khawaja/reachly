"""initial schema: businesses, meetings

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE businesses (
          id            SERIAL PRIMARY KEY,
          name          TEXT NOT NULL,
          phone         TEXT,
          email         TEXT,
          website       TEXT,
          business_type TEXT,
          city          TEXT,
          country       TEXT,
          channel       TEXT NOT NULL DEFAULT 'phone',
          status        TEXT NOT NULL DEFAULT 'new',
          notes         TEXT,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE meetings (
          id            SERIAL PRIMARY KEY,
          business_id   INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
          scheduled_at  TIMESTAMPTZ NOT NULL,
          notes         TEXT,
          done          BOOLEAN NOT NULL DEFAULT false,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_businesses_status ON businesses(status)")
    op.execute("CREATE INDEX idx_meetings_business ON meetings(business_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS meetings")
    op.execute("DROP TABLE IF EXISTS businesses")
