"""summaries: Resumo da Compactação (ticket 12, ADR 0006).

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Um Resumo cobre as Mensagens da Conversa até `ate_message_id`, inclusive. O mais novo vale.
    op.execute(
        """
        CREATE TABLE summaries (
            id bigserial PRIMARY KEY,
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            ate_message_id bigint NOT NULL,
            texto text NOT NULL,
            tokens int NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_summaries_conversation ON summaries (conversation_id, id DESC)")
    op.execute("GRANT SELECT, INSERT ON summaries TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE summaries_id_seq TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE summaries")
