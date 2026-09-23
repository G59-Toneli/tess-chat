"""audit_events somente-inserção para tess_app (ADR 0007).

Revision ID: 0001
Revises:
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_events (
            id bigserial PRIMARY KEY,
            ts timestamptz NOT NULL DEFAULT now(),
            user_id uuid NULL,
            conversation_id uuid NULL,
            event_type text NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}',
            input_tokens int NULL,
            output_tokens int NULL,
            cost_micro_usd bigint NULL,
            latency_ms int NULL,
            model text NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_audit_events_ts ON audit_events (ts)")
    op.execute("CREATE INDEX ix_audit_events_conversation_ts ON audit_events (conversation_id, ts)")
    # tess_app só insere e lê. A sequence é necessária para o INSERT gerar o id.
    op.execute("GRANT INSERT, SELECT ON audit_events TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE audit_events_id_seq TO tess_app")
    op.execute("REVOKE UPDATE, DELETE ON audit_events FROM tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE audit_events")
