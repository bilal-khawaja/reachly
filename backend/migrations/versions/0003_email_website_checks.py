"""email/website: blank -> NULL, enforce format when present

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16
"""
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validators import EMAIL_PG, WEBSITE_PG  # noqa: E402

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE businesses SET email = NULL WHERE btrim(email) = ''"))
    bind.execute(sa.text("UPDATE businesses SET website = NULL WHERE btrim(website) = ''"))
    bind.execute(sa.text("ALTER TABLE businesses ALTER COLUMN email SET DEFAULT NULL"))
    bind.execute(sa.text("ALTER TABLE businesses ALTER COLUMN website SET DEFAULT NULL"))
    bind.execute(
        sa.text(f"ALTER TABLE businesses ADD CONSTRAINT businesses_email_format CHECK (email IS NULL OR email ~ '{EMAIL_PG}')")
    )
    bind.execute(
        sa.text(f"ALTER TABLE businesses ADD CONSTRAINT businesses_website_format CHECK (website IS NULL OR website ~ '{WEBSITE_PG}')")
    )


def downgrade() -> None:
    op.execute("ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_website_format")
    op.execute("ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_email_format")
