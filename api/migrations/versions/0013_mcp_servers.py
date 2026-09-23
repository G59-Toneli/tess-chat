"""mcp_servers: Servidor MCP por Usuário; tools de origem 'mcp' ligadas ao servidor (ticket 17, ADR 0009).

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `headers` é JSON {nome: valor} cifrado com Fernet (CONNECTORS_KEY). Nunca em claro no banco.
    op.execute(
        """
        CREATE TABLE mcp_servers (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            nome text NOT NULL,
            url text NOT NULL,
            headers text NOT NULL,
            ativo boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, nome)
        )
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON mcp_servers TO tess_app")
    # Tool MCP pertence a um servidor: apagar o servidor leva as tools e os toggles por Conversa.
    op.execute("ALTER TABLE tools ADD COLUMN mcp_server_id uuid REFERENCES mcp_servers(id) ON DELETE CASCADE")
    op.execute(
        "ALTER TABLE tools ADD CONSTRAINT tools_mcp_server_check CHECK ((origem = 'mcp') = (mcp_server_id IS NOT NULL))"
    )
    # A app passa a inserir e apagar linhas do registro, mas só as de origem 'mcp' (RLS).
    # As nativas e as do Google seguem fora do alcance da app, como a 0008 queria.
    op.execute("GRANT INSERT, DELETE ON tools TO tess_app")
    op.execute("ALTER TABLE tools ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tools_ler ON tools FOR SELECT TO tess_app USING (true)")
    op.execute("CREATE POLICY tools_toggle ON tools FOR UPDATE TO tess_app USING (true)")
    op.execute("CREATE POLICY tools_mcp_insere ON tools FOR INSERT TO tess_app WITH CHECK (origem = 'mcp')")
    op.execute("CREATE POLICY tools_mcp_apaga ON tools FOR DELETE TO tess_app USING (origem = 'mcp')")


def downgrade() -> None:
    op.execute("DROP POLICY tools_mcp_apaga ON tools")
    op.execute("DROP POLICY tools_mcp_insere ON tools")
    op.execute("DROP POLICY tools_toggle ON tools")
    op.execute("DROP POLICY tools_ler ON tools")
    op.execute("ALTER TABLE tools DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE INSERT, DELETE ON tools FROM tess_app")
    op.execute("DELETE FROM tools WHERE origem = 'mcp'")
    op.execute("ALTER TABLE tools DROP CONSTRAINT tools_mcp_server_check")
    op.execute("ALTER TABLE tools DROP COLUMN mcp_server_id")
    op.execute("DROP TABLE mcp_servers")
