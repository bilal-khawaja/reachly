"""per-user leads: businesses.user_id

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-25
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE businesses ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
    op.execute("UPDATE businesses SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1) WHERE user_id IS NULL")
    op.execute("ALTER TABLE businesses ALTER COLUMN user_id SET NOT NULL")
    op.execute("CREATE INDEX businesses_user_id_idx ON businesses (user_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS businesses_user_id_idx")
    op.execute("ALTER TABLE businesses DROP COLUMN user_id")
