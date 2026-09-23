"""Compartilhamento: link público somente-leitura cortado na última Mensagem (ADR 0008)."""

import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.auth import User, current_user
from app.conversas import Conversation, Message, conversa_do_usuario
from app.db import Base, get_session

NOINDEX = {"X-Robots-Tag": "noindex"}
INDEX_HTML = Path(__file__).resolve().parents[2] / "web" / "dist" / "index.html"
HTML_SEM_BUILD = "<!doctype html><title>Conversa compartilhada</title>"


class Share(Base):
    __tablename__ = "shares"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Nulo quando a Conversa não tinha Mensagem: o link mostra vazio.
    last_message_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShareOut(BaseModel):
    id: str
    url: str
    conversation_id: uuid.UUID
    title: str
    created_at: datetime


class MensagemPublica(BaseModel):
    id: int
    role: str
    parts: list[dict[str, Any]]
    created_at: datetime


class SharePublico(BaseModel):
    title: str
    shared_by: str
    created_at: datetime
    messages: list[MensagemPublica]


Sessao = Annotated[AsyncSession, Depends(get_session)]
Usuario = Annotated[User, Depends(current_user)]

router = APIRouter(tags=["compartilhamento"])


def _out(share: Share, title: str) -> ShareOut:
    return ShareOut(
        id=share.id,
        url=f"/s/{share.id}",
        conversation_id=share.conversation_id,
        title=title,
        created_at=share.created_at,
    )


# REVISAR(human): 404 único para revogado e inexistente. Mesmo corpo, mesmo header:
# quem tem um link revogado não descobre que ele existiu (ADR 0008).
async def _share_ativo(session: AsyncSession, share_id: str) -> tuple[Share, Conversation, User]:
    linha = (
        await session.execute(
            select(Share, Conversation, User)
            .join(Conversation, Conversation.id == Share.conversation_id)
            .join(User, User.id == Share.owner_id)
            .where(Share.id == share_id, Share.revoked_at.is_(None))
        )
    ).first()
    if linha is None:
        raise HTTPException(status_code=404, detail="Link não encontrado", headers=NOINDEX)
    share, conv, dono = linha
    return share, conv, dono


# REVISAR(human): o corte é o maior id de Mensagem no momento do share.
# messages.id é bigserial: Mensagem nova sempre tem id maior e fica fora do link.
@router.post("/api/conversations/{cid}/share", status_code=201, response_model=ShareOut)
async def criar(cid: uuid.UUID, session: Sessao, user: Usuario) -> ShareOut:
    conv = await conversa_do_usuario(session, user, cid)
    corte = await session.scalar(select(func.max(Message.id)).where(Message.conversation_id == cid))
    share = Share(id=secrets.token_urlsafe(16), conversation_id=cid, owner_id=user.id, last_message_id=corte)
    session.add(share)
    await session.flush()
    await audit(
        session, "share_created", user_id=user.id, conversation_id=cid,
        payload={"share_id": share.id, "last_message_id": corte},
    )
    await session.commit()
    await session.refresh(share)
    return _out(share, conv.title)


@router.get("/api/shares", response_model=list[ShareOut])
async def listar(session: Sessao, user: Usuario) -> list[ShareOut]:
    """Meus links ativos, do mais recente para o mais antigo."""
    linhas = await session.execute(
        select(Share, Conversation.title)
        .join(Conversation, Conversation.id == Share.conversation_id)
        .where(Share.owner_id == user.id, Share.revoked_at.is_(None))
        .order_by(Share.created_at.desc())
    )
    return [_out(s, t) for s, t in linhas.all()]


@router.delete("/api/shares/{share_id}", status_code=204)
async def revogar(share_id: str, session: Sessao, user: Usuario) -> Response:
    share = await session.scalar(
        select(Share).where(Share.id == share_id, Share.owner_id == user.id, Share.revoked_at.is_(None))
    )
    if share is None:
        raise HTTPException(status_code=404, detail="Link não encontrado")
    share.revoked_at = func.now()
    await audit(
        session, "share_revoked", user_id=user.id, conversation_id=share.conversation_id,
        payload={"share_id": share_id},
    )
    await session.commit()
    return Response(status_code=204)


@router.get("/api/s/{share_id}", response_model=SharePublico)
async def publico(share_id: str, session: Sessao, response: Response) -> SharePublico:
    """Sem auth. Mensagens até o corte."""
    share, conv, dono = await _share_ativo(session, share_id)
    msgs: list[Message] = []
    if share.last_message_id is not None:
        q = (
            select(Message)
            .where(Message.conversation_id == conv.id, Message.id <= share.last_message_id)
            .order_by(Message.created_at, Message.id)
        )
        msgs = list((await session.scalars(q)).all())
    response.headers.update(NOINDEX)
    return SharePublico(
        title=conv.title,
        # Só a parte antes do @: o link é público, o e-mail inteiro não.
        shared_by=dono.email.split("@")[0],
        created_at=share.created_at,
        messages=[MensagemPublica.model_validate(m, from_attributes=True) for m in msgs],
    )


@router.get("/s/{share_id}", include_in_schema=False)
async def pagina(share_id: str, session: Sessao) -> HTMLResponse:
    """Serve o front (SPA) com noindex. Link inválido: mesmo HTML, status 404; o front mostra o aviso."""
    try:
        await _share_ativo(session, share_id)
        status = 200
    except HTTPException:
        status = 404
    html = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.is_file() else HTML_SEM_BUILD
    return HTMLResponse(html, status_code=status, headers=NOINDEX)
