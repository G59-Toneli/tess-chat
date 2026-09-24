"""api_tools: Tool por API por Usuário; tools de origem 'api' ligadas à linha (ticket 59, ADR 0024).

Revision ID: 0023
Revises: 0022
"""

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `auth` é JSON {tipo, nome?, valor?, token?} cifrado com Fernet (CONNECTORS_KEY). Nunca em claro no banco.
    op.execute(
        """
        CREATE TABLE api_tools (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            nome text NOT NULL,
            descricao text NOT NULL,
            metodo text NOT NULL CHECK (metodo IN ('GET', 'POST')),
            url text NOT NULL,
            parametros jsonb NOT NULL,
            corpo jsonb,
            auth text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, nome)
        )
        """
    )
    op.execute("GRANT SELECT, INSERT, DELETE ON api_tools TO tess_app")
    op.execute("ALTER TABLE tools DROP CONSTRAINT tools_origem_check")
    op.execute("ALTER TABLE tools ADD CONSTRAINT tools_origem_check CHECK (origem IN ('nativa', 'mcp', 'google', 'api'))")
    # Tool de API pertence a uma linha: apagar a linha leva a tool e os toggles por Conversa.
    op.execute("ALTER TABLE tools ADD COLUMN api_tool_id uuid REFERENCES api_tools(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE tools ADD CONSTRAINT tools_api_tool_check CHECK ((origem = 'api') = (api_tool_id IS NOT NULL))")
    # Mesmo padrão da 0013: a app insere e apaga só as linhas da própria origem.
    op.execute("CREATE POLICY tools_api_insere ON tools FOR INSERT TO tess_app WITH CHECK (origem = 'api')")
    op.execute("CREATE POLICY tools_api_apaga ON tools FOR DELETE TO tess_app USING (origem = 'api')")


def downgrade() -> None:
    op.execute("DROP POLICY tools_api_apaga ON tools")
    op.execute("DROP POLICY tools_api_insere ON tools")
    op.execute("DELETE FROM tools WHERE origem = 'api'")
    op.execute("ALTER TABLE tools DROP CONSTRAINT tools_api_tool_check")
    op.execute("ALTER TABLE tools DROP COLUMN api_tool_id")
    op.execute("ALTER TABLE tools DROP CONSTRAINT tools_origem_check")
    op.execute("ALTER TABLE tools ADD CONSTRAINT tools_origem_check CHECK (origem IN ('nativa', 'mcp', 'google'))")
    op.execute("DROP TABLE api_tools")
