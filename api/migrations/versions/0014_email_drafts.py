"""email_drafts: Rascunho de e-mail que só sai com clique do dono; Tool gmail_send (ticket 25, ADR 0013).

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A Mensagem do assistente só nasce no fim do turno: o Rascunho liga-se ao tool_call_id,
    # que é a chave da parte da tool dentro da Mensagem.
    op.execute(
        """
        CREATE TABLE email_drafts (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            tool_call_id text,
            para text NOT NULL,
            assunto text NOT NULL,
            corpo text NOT NULL,
            thread_id text,
            in_reply_to text,
            referencias text,
            estado text NOT NULL DEFAULT 'pendente' CHECK (estado IN ('pendente', 'enviado', 'descartado')),
            gmail_message_id text,
            created_at timestamptz NOT NULL DEFAULT now(),
            decidido_em timestamptz
        )
        """
    )
    op.execute("CREATE INDEX email_drafts_conversa ON email_drafts (conversation_id)")
    # Sem DELETE: descartar é mudança de estado, o Rascunho fica como registro.
    op.execute("GRANT SELECT, INSERT, UPDATE ON email_drafts TO tess_app")
    # Tool com efeito fora do app nasce desligada em toda Conversa nova.
    op.execute("ALTER TABLE tools ADD COLUMN padrao_ligada boolean NOT NULL DEFAULT true")
    op.execute(
        """
        INSERT INTO tools (nome, origem, descricao, schema, padrao_ligada) VALUES
        ('gmail_send', 'google', 'Prepara um e-mail para o usuário enviar pelo Gmail dele. NÃO envia: cria um rascunho que o usuário confirma com um clique na tela. Para responder um e-mail lido com gmail_read, passe o thread_id dele e use "Re: <assunto original>". Depois de chamar, diga ao usuário que o rascunho está na tela aguardando o clique em Enviar.',
         '{"type": "object", "properties": {"para": {"type": "string"}, "assunto": {"type": "string"}, "corpo": {"type": "string"}, "thread_id": {"type": "string"}}, "required": ["para", "assunto", "corpo"]}',
         false)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM tools WHERE nome = 'gmail_send'")
    op.execute("ALTER TABLE tools DROP COLUMN padrao_ligada")
    op.execute("DROP TABLE email_drafts")
