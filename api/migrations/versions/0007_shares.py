"""shares: Compartilhamento por link com corte na última Mensagem (ticket 13, ADR 0008).

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE shares (
            id text PRIMARY KEY,
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            last_message_id bigint NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_shares_owner_created ON shares (owner_id, created_at DESC)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON shares TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE shares")
