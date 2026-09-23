"""Descrição de drive_search_read com PDF e recentes volta a morar só no banco (ticket 42).

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels = None
depends_on = None

# Texto que o ticket 39 pôs em conectores.DESCRICOES.
DESCRICAO = (
    "Busca arquivos no Google Drive do usuário pelo nome ou conteúdo e devolve o texto do arquivo mais "
    "relevante (Docs, Sheets, Slides, texto ou PDF), mais a lista dos outros achados com data de criação "
    "e de modificação. Com query vazia, lista os 10 arquivos modificados mais recentemente, com as datas, "
    "sem ler conteúdo: use para 'últimos arquivos', 'recentes', 'de hoje'."
)
DESCRICAO_USUARIO = "Procura arquivos e PDFs no seu Google Drive e lê o mais relevante, ou lista os recentes."
# Textos anteriores: 0012 e 0016.
ANTES = (
    "Busca arquivos no Google Drive do usuário pelo nome ou conteúdo e devolve o texto do arquivo mais "
    "relevante (Docs, Sheets, Slides e arquivos de texto), mais a lista dos outros achados."
)
ANTES_USUARIO = "Procura arquivos no seu Google Drive e lê o mais relevante."


def _gravar(descricao: str, descricao_usuario: str) -> None:
    op.execute(
        sa.text(
            "UPDATE tools SET descricao = :d, descricao_usuario = :u WHERE nome = 'drive_search_read'"
        ).bindparams(d=descricao, u=descricao_usuario)
    )


def upgrade() -> None:
    _gravar(DESCRICAO, DESCRICAO_USUARIO)


def downgrade() -> None:
    _gravar(ANTES, ANTES_USUARIO)
