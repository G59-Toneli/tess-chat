"""Descrição da Tool para o Usuário, separada da descrição que o modelo recebe (ticket 28).

Revision ID: 0016
Revises: 0015
"""

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels = None
depends_on = None

# Voz do produto, sem instrução ao modelo. O modelo continua recebendo tools.descricao.
TEXTOS = {
    "web_search": "Busca na web e cita as fontes.",
    "web_fetch": "Abre uma página da web e lê o conteúdo.",
    "gmail_search": "Procura e-mails no seu Gmail.",
    "gmail_read": "Abre um e-mail do seu Gmail e lê o conteúdo.",
    "drive_search_read": "Procura arquivos no seu Google Drive e lê o mais relevante.",
    "gmail_send": "Prepara um rascunho de e-mail. Ele só sai quando você clica em Enviar.",
}


def upgrade() -> None:
    op.execute("ALTER TABLE tools ADD COLUMN descricao_usuario text")
    for nome, texto in TEXTOS.items():
        op.execute(f"UPDATE tools SET descricao_usuario = '{texto}' WHERE nome = '{nome}'")
    # Tools MCP: a descrição do servidor, cortada em 140 caracteres (mesma regra do cadastro).
    op.execute("UPDATE tools SET descricao_usuario = left(descricao, 140) WHERE descricao_usuario IS NULL")
    op.execute("ALTER TABLE tools ALTER COLUMN descricao_usuario SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE tools DROP COLUMN descricao_usuario")
