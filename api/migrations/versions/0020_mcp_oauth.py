"""mcp_servers: credencial OAuth cifrada e estado da conexão (ticket 52, ADR 0022).

Revision ID: 0020
Revises: 0019
"""

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `oauth`: JSON cifrado com Fernet (client_id, token_endpoint, refresh_token, expires_at...). Nulo: cadastro por header.
    op.execute("ALTER TABLE mcp_servers ADD COLUMN oauth text")
    op.execute(
        "ALTER TABLE mcp_servers ADD COLUMN estado text NOT NULL DEFAULT 'ok' "
        "CHECK (estado IN ('ok', 'aguardando_oauth', 'expirado'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE mcp_servers DROP COLUMN estado")
    op.execute("ALTER TABLE mcp_servers DROP COLUMN oauth")
