"""tools: app pode alternar ativa_global (ticket 07b).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Só a coluna do toggle. Nome, descrição e schema continuam fora do alcance da app.
    op.execute("GRANT UPDATE (ativa_global) ON tools TO tess_app")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (ativa_global) ON tools FROM tess_app")
