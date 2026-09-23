"""Preço do gemini-3.7-flash, reserva do fallback (ticket 06b, ADR 0012).

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # research/02 seção 1.3: mesmo preço do 3.8 (INFERIDO).
    op.execute(
        """
        INSERT INTO price_table
            (model, input_micro_usd_1m, output_micro_usd_1m, cache_micro_usd_1m, thinking_micro_usd_1m, vigente_desde)
        VALUES ('gemini-3.7-flash', 750000, 3750000, 75000, 3750000, '2026-09-01T00:00:00Z')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM price_table WHERE model = 'gemini-3.7-flash'")
