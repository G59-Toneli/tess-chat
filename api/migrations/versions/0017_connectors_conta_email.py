"""Conta Google vinculada e Gmail disponível no Conector (ticket 29).

Revision ID: 0017
Revises: 0016
"""

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nulo: conexão anterior a este ticket. O card pede para reconectar.
    op.execute("ALTER TABLE connectors ADD COLUMN conta_email text")
    # true por padrão: conexão antiga mantém as tools do Gmail.
    op.execute("ALTER TABLE connectors ADD COLUMN gmail_disponivel boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    op.execute("ALTER TABLE connectors DROP COLUMN gmail_disponivel")
    op.execute("ALTER TABLE connectors DROP COLUMN conta_email")
