"""gmail_send nasce ligada por Conversa (decisão do Toneli, 23/09; emenda o ADR 0013 item 6).

Revision ID: 0015
Revises: 0014
"""

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A trava contra envio indevido é o clique em Enviar, não o toggle. Ligada por padrão não muda o risco.
    op.execute("UPDATE tools SET padrao_ligada = true WHERE nome = 'gmail_send'")


def downgrade() -> None:
    op.execute("UPDATE tools SET padrao_ligada = false WHERE nome = 'gmail_send'")
