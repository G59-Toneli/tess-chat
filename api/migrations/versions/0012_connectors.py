"""connectors: Conector Google por Usuário, e as três Tools do Google no registro (ticket 18, ADR 0010).

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `tokens` é JSON {access_token, refresh_token} cifrado com Fernet. Nunca em claro no banco.
    op.execute(
        """
        CREATE TABLE connectors (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provedor text NOT NULL CHECK (provedor IN ('google')),
            tokens text NOT NULL,
            escopos text[] NOT NULL,
            expira_em timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, provedor)
        )
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON connectors TO tess_app")
    # Origem própria: a Tool só existe para quem tem Conector ativo.
    op.execute("ALTER TABLE tools DROP CONSTRAINT tools_origem_check")
    op.execute("ALTER TABLE tools ADD CONSTRAINT tools_origem_check CHECK (origem IN ('nativa', 'mcp', 'google'))")
    op.execute(
        """
        INSERT INTO tools (nome, origem, descricao, schema) VALUES
        ('gmail_search', 'google', 'Busca e-mails no Gmail do usuário (sintaxe de busca do Gmail, ex.: "from:ana fatura"). Devolve id, remetente, assunto, data e trecho dos mais recentes. Use gmail_read com o id para ler o corpo.',
         '{"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}'),
        ('gmail_read', 'google', 'Lê um e-mail do Gmail do usuário pelo id devolvido em gmail_search. Devolve cabeçalhos e corpo em texto.',
         '{"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"]}'),
        ('drive_search_read', 'google', 'Busca arquivos no Google Drive do usuário pelo nome ou conteúdo e devolve o texto do arquivo mais relevante (Docs, Sheets, Slides e arquivos de texto), mais a lista dos outros achados.',
         '{"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM tools WHERE origem = 'google'")
    op.execute("ALTER TABLE tools DROP CONSTRAINT tools_origem_check")
    op.execute("ALTER TABLE tools ADD CONSTRAINT tools_origem_check CHECK (origem IN ('nativa', 'mcp'))")
    op.execute("DROP TABLE connectors")
