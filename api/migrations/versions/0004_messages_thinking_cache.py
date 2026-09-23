"""messages ganha thinking_tokens e cache_read_tokens (ticket 06).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE messages ADD COLUMN thinking_tokens int NULL")
    op.execute("ALTER TABLE messages ADD COLUMN cache_read_tokens int NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE messages DROP COLUMN cache_read_tokens")
    op.execute("ALTER TABLE messages DROP COLUMN thinking_tokens")
