"""tools e conversation_tools: registro único de Tools com toggle por Conversa (ticket 10, ADR 0009).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tools (
            nome text PRIMARY KEY,
            origem text NOT NULL CHECK (origem IN ('nativa', 'mcp')),
            descricao text NOT NULL,
            schema jsonb NOT NULL,
            ativa_global boolean NOT NULL DEFAULT true
        )
        """
    )
    op.execute(
        """
        INSERT INTO tools (nome, origem, descricao, schema) VALUES
        ('web_search', 'nativa', 'Busca na web (Tavily). Devolve título, URL e trecho de cada resultado. Cite na resposta as URLs usadas.',
         '{"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}'),
        ('web_fetch', 'nativa', 'Baixa uma URL e devolve o texto limpo (Jina Reader, fallback trafilatura).',
         '{"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}')
        """
    )
    op.execute(
        """
        CREATE TABLE conversation_tools (
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            tool_nome text NOT NULL REFERENCES tools(nome) ON DELETE CASCADE,
            ativa boolean NOT NULL,
            PRIMARY KEY (conversation_id, tool_nome)
        )
        """
    )
    op.execute("GRANT SELECT ON tools TO tess_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conversation_tools TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE conversation_tools")
    op.execute("DROP TABLE tools")
