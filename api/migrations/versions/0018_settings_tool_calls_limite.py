"""Teto de tool calls na Configuração (ticket 30).

Revision ID: 0018
Revises: 0017
"""

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nulo herda do escopo de cima, como as outras colunas de settings.
    op.execute("ALTER TABLE settings ADD COLUMN tool_calls_limite int NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE settings DROP COLUMN tool_calls_limite")
