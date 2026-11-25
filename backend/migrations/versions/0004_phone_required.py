"""phone is required

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-16
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE businesses ALTER COLUMN phone SET NOT NULL")
    op.execute("ALTER TABLE businesses ADD CONSTRAINT businesses_phone_not_blank CHECK (btrim(phone) <> '')")


def downgrade() -> None:
    op.execute("ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_phone_not_blank")
    op.execute("ALTER TABLE businesses ALTER COLUMN phone DROP NOT NULL")
