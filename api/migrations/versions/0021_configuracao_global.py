"""configuracao_global: chave global cadastro_aberto (revisão final, A4).

Revision ID: 0021
Revises: 0020
"""

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Linha única (id = 1). `settings` não serve: o CHECK exige Usuário ou Conversa em toda linha.
    op.execute(
        """
        CREATE TABLE configuracao_global (
            id int PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            cadastro_aberto boolean NOT NULL DEFAULT true,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("INSERT INTO configuracao_global DEFAULT VALUES")
    op.execute("GRANT SELECT, UPDATE ON configuracao_global TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE configuracao_global")
