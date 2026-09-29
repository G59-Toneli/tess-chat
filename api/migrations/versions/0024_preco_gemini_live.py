"""Preço do gemini-3.8-live por modalidade (ticket 76, ADR 0027).

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nulo nos modelos de texto: só a Ligação cobra áudio e imagem à parte.
    op.execute(
        """
        ALTER TABLE price_table
            ADD COLUMN audio_input_micro_usd_1m bigint NULL,
            ADD COLUMN image_input_micro_usd_1m bigint NULL,
            ADD COLUMN audio_output_micro_usd_1m bigint NULL
        """
    )
    # Pricing de 28/09 (ADR 0027): texto 0,75/4,50, áudio in 3, imagem in 1, áudio out 12.
    # Pensamento ao preço de texto de saída: INFERIDO (spike 75). Cache não usado na Ligação.
    op.execute(
        """
        INSERT INTO price_table
            (model, input_micro_usd_1m, output_micro_usd_1m, cache_micro_usd_1m, thinking_micro_usd_1m,
             audio_input_micro_usd_1m, image_input_micro_usd_1m, audio_output_micro_usd_1m, vigente_desde)
        VALUES ('gemini-3.8-live', 750000, 4500000, 0, 4500000, 3000000, 1000000, 12000000, '2026-09-01T00:00:00Z')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM price_table WHERE model = 'gemini-3.8-live'")
    op.execute(
        """
        ALTER TABLE price_table
            DROP COLUMN audio_input_micro_usd_1m,
            DROP COLUMN image_input_micro_usd_1m,
            DROP COLUMN audio_output_micro_usd_1m
        """
    )
