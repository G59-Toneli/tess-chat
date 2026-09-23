"""Conversas, Mensagens e Anexos. Usuário só vê o que é dele."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.auth import User, current_user
from app.db import Base, get_session

TITULO_PADRAO = "Nova conversa"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text, default=TITULO_PADRAO)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(Text)  # user | assistant | tool
    parts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    input_tokens: Mapped[int | None]
    # Já inclui thinking (RunUsage.output_tokens).
    output_tokens: Mapped[int | None]
    thinking_tokens: Mapped[int | None]
    cache_read_tokens: Mapped[int | None]
    model: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Attachment(Base):
    """Metadados. O arquivo fica em disco, em `path`."""

    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Nulo entre o upload e o envio da Mensagem.
    message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("messages.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversaIn(BaseModel):
    title: str = Field(default=TITULO_PADRAO, min_length=1, max_length=200)


class ConversaRenomear(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ConversaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MensagemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    parts: list[dict[str, Any]]
    input_tokens: int | None
    output_tokens: int | None
    thinking_tokens: int | None
    cache_read_tokens: int | None
    model: str | None
    created_at: datetime


Sessao = Annotated[AsyncSession, Depends(get_session)]
Usuario = Annotated[User, Depends(current_user)]

router = APIRouter(prefix="/api/conversations", tags=["conversas"])


# REVISAR(human): conversa de outro usuário responde 404, igual a inexistente.
# O filtro por user_id vai na própria query: um caminho só, sem vazar existência.
async def conversa_do_usuario(session: AsyncSession, user: User, cid: uuid.UUID) -> Conversation:
    """Carrega a Conversa se ela é do Usuário. Senão, 404."""
    conv = await session.scalar(
        select(Conversation).where(Conversation.id == cid, Conversation.user_id == user.id)
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return conv


@router.get("", response_model=list[ConversaOut])
async def listar(session: Sessao, user: Usuario) -> list[Conversation]:
    """Conversas do Usuário, da mais recente para a mais antiga."""
    q = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
    )
    return list((await session.scalars(q)).all())


@router.post("", status_code=201, response_model=ConversaOut)
async def criar(body: ConversaIn, session: Sessao, user: Usuario) -> Conversation:
    conv = Conversation(user_id=user.id, title=body.title)
    session.add(conv)
    await session.flush()
    await audit(session, "conversation_created", user_id=user.id, conversation_id=conv.id)
    await session.commit()
    await session.refresh(conv)
    return conv


@router.get("/{cid}", response_model=ConversaOut)
async def obter(cid: uuid.UUID, session: Sessao, user: Usuario) -> Conversation:
    return await conversa_do_usuario(session, user, cid)


@router.patch("/{cid}", response_model=ConversaOut)
async def renomear(
    cid: uuid.UUID, body: ConversaRenomear, session: Sessao, user: Usuario
) -> Conversation:
    conv = await conversa_do_usuario(session, user, cid)
    conv.title = body.title
    await session.commit()
    await session.refresh(conv)
    return conv


# REVISAR(human): remoção física, com CASCADE para mensagens e anexos.
# O evento guarda o conversation_id; audit_events não tem FK, então sobrevive.
@router.delete("/{cid}", status_code=204)
async def apagar(cid: uuid.UUID, session: Sessao, user: Usuario) -> Response:
    conv = await conversa_do_usuario(session, user, cid)
    await session.delete(conv)
    await audit(session, "conversation_deleted", user_id=user.id, conversation_id=cid)
    await session.commit()
    return Response(status_code=204)


@router.get("/{cid}/messages", response_model=list[MensagemOut])
async def listar_mensagens(cid: uuid.UUID, session: Sessao, user: Usuario) -> list[Message]:
    """Mensagens na ordem de criação. Desempate pelo id (now() é fixo na transação)."""
    await conversa_do_usuario(session, user, cid)
    q = (
        select(Message)
        .where(Message.conversation_id == cid)
        .order_by(Message.created_at, Message.id)
    )
    return list((await session.scalars(q)).all())
