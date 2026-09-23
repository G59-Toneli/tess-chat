"""settings: Configuração por Usuário e por Conversa (ticket 14).

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Uma linha por escopo: Usuário ou Conversa, nunca os dois. Coluna nula herda do escopo de cima.
    # Cap por Usuário fica em `caps` (ticket 08), fonte única do Crédito.
    op.execute(
        """
        CREATE TABLE settings (
            id bigserial PRIMARY KEY,
            user_id uuid NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id uuid NULL REFERENCES conversations(id) ON DELETE CASCADE,
            modelo text NULL,
            nivel_raciocinio text NULL,
            compactacao_limiar int NULL,
            roteador_limiar double precision NULL,
            updated_at timestamptz NOT NULL DEFAULT now(),
            CHECK ((user_id IS NULL) <> (conversation_id IS NULL)),
            UNIQUE NULLS NOT DISTINCT (user_id, conversation_id)
        )
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON settings TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE settings_id_seq TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE settings")
