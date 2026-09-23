"""mcp_servers: apaga os pendentes do OAuth abandonado (ticket 57, ADR 0022).

Revision ID: 0022
Revises: 0021
"""

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # O pendente agora mora no cookie. Linha `aguardando_oauth` sem tools é consentimento que nunca voltou.
    op.execute(
        "DELETE FROM mcp_servers s WHERE s.estado = 'aguardando_oauth' "
        "AND NOT EXISTS (SELECT 1 FROM tools t WHERE t.mcp_server_id = s.id)"
    )


def downgrade() -> None:
    pass  # linha apagada não volta
