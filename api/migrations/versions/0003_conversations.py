"""conversations, messages, attachments (ticket 05).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE conversations (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_conversations_user_updated ON conversations (user_id, updated_at DESC)")
    op.execute(
        """
        CREATE TABLE messages (
            id bigserial PRIMARY KEY,
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role text NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
            parts jsonb NOT NULL,
            input_tokens int NULL,
            output_tokens int NULL,
            model text NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_messages_conversation_created ON messages (conversation_id, created_at, id)")
    op.execute(
        """
        CREATE TABLE attachments (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message_id bigint NULL REFERENCES messages(id) ON DELETE CASCADE,
            filename text NOT NULL,
            mime_type text NOT NULL,
            size_bytes bigint NOT NULL,
            path text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_attachments_message ON attachments (message_id)")
    for tabela in ("conversations", "messages", "attachments"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabela} TO tess_app")
    op.execute("GRANT USAGE ON SEQUENCE messages_id_seq TO tess_app")


def downgrade() -> None:
    op.execute("DROP TABLE attachments")
    op.execute("DROP TABLE messages")
    op.execute("DROP TABLE conversations")
