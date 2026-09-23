"""price_table, credit_ledger somente-inserção e caps (ticket 08, ADR 0004).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Preço em micro-USD por 1M de tokens. Nova vigência é linha nova; linha antiga não muda.
    op.execute(
        """
        CREATE TABLE price_table (
            id bigserial PRIMARY KEY,
            model text NOT NULL,
            input_micro_usd_1m bigint NOT NULL,
            output_micro_usd_1m bigint NOT NULL,
            cache_micro_usd_1m bigint NOT NULL,
            thinking_micro_usd_1m bigint NOT NULL,
            vigente_desde timestamptz NOT NULL,
            UNIQUE (model, vigente_desde)
        )
        """
    )
    # research/02 seção 1.3 e ADR 0003. Jev: só input, US$ 0,042/1M.
    op.execute(
        """
        INSERT INTO price_table
            (model, input_micro_usd_1m, output_micro_usd_1m, cache_micro_usd_1m, thinking_micro_usd_1m, vigente_desde)
        VALUES
            ('gemini-3.8-flash', 750000, 3750000, 75000, 3750000, '2026-09-01T00:00:00Z'),
            ('gemini-3.1-flash-lite', 250000, 1500000, 25000, 1500000, '2026-09-01T00:00:00Z'),
            ('jev-latest', 42000, 0, 0, 0, '2026-09-01T00:00:00Z')
        """
    )
    # Sem FK: o Ledger sobrevive à remoção da Conversa.
    op.execute(
        """
        CREATE TABLE credit_ledger (
            id bigserial PRIMARY KEY,
            ts timestamptz NOT NULL DEFAULT now(),
            user_id uuid NOT NULL,
            conversation_id uuid NULL,
            message_id bigint NULL,
            model text NOT NULL,
            price_id bigint NOT NULL REFERENCES price_table (id),
            input_tokens int NOT NULL,
            output_tokens int NOT NULL,
            thinking_tokens int NOT NULL,
            cache_read_tokens int NOT NULL,
            cost_micro_usd bigint NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_credit_ledger_user ON credit_ledger (user_id)")
    op.execute("CREATE INDEX ix_credit_ledger_conversation ON credit_ledger (conversation_id)")
    # user_id NULL é o Cap global.
    op.execute(
        """
        CREATE TABLE caps (
            id bigserial PRIMARY KEY,
            user_id uuid NULL,
            limite_micro_usd bigint NOT NULL,
            UNIQUE NULLS NOT DISTINCT (user_id)
        )
        """
    )
    op.execute("GRANT SELECT, INSERT ON price_table TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE price_table_id_seq TO tess_app")
    op.execute("GRANT SELECT, INSERT ON credit_ledger TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE credit_ledger_id_seq TO tess_app")
    op.execute("REVOKE UPDATE, DELETE ON price_table, credit_ledger FROM tess_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON caps TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE caps_id_seq TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE caps")
    op.execute("DROP TABLE credit_ledger")
    op.execute("DROP TABLE price_table")
