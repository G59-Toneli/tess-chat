"""Leitura da auditoria e visão de admin (ticket 15, ADR 0007)."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import AuditEvent
from app.auth import User, current_superuser, current_user
from app.credito import CreditLedger, _cap
from app.db import get_session

router = APIRouter(tags=["auditoria"])
Sessao = Annotated[AsyncSession, Depends(get_session)]


class EventoOut(BaseModel):
    id: int
    ts: datetime
    user_id: uuid.UUID | None
    user_email: str | None
    conversation_id: uuid.UUID | None
    event_type: str
    payload: dict[str, Any]
    input_tokens: int | None
    output_tokens: int | None
    cost_micro_usd: int | None
    latency_ms: int | None
    model: str | None


class PaginaEventos(BaseModel):
    items: list[EventoOut]
    total: int
    limit: int
    offset: int


# quem vê o quê. Usuário comum: o filtro de usuário é forçado para ele
# mesmo, o parâmetro user_id é ignorado. Admin (is_superuser): sem user_id vê tudo,
# inclusive eventos sem usuário (login_failed de e-mail inexistente).
def _escopo(user: User, user_id: uuid.UUID | None) -> list[Any]:
    if not user.is_superuser:
        return [AuditEvent.user_id == user.id]
    return [AuditEvent.user_id == user_id] if user_id is not None else []


@router.get("/api/audit")
async def listar_eventos(
    session: Sessao,
    user: Annotated[User, Depends(current_user)],
    user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    event_type: str | None = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginaEventos:
    """Eventos do mais recente para o mais antigo. `ts` empata na mesma transação: `id` desempata."""
    filtro = _escopo(user, user_id)
    if conversation_id is not None:
        filtro.append(AuditEvent.conversation_id == conversation_id)
    if event_type:
        filtro.append(AuditEvent.event_type == event_type)
    if desde is not None:
        filtro.append(AuditEvent.ts >= desde)
    if ate is not None:
        filtro.append(AuditEvent.ts <= ate)

    total = await session.scalar(select(func.count()).select_from(AuditEvent).where(*filtro))
    linhas = await session.execute(
        select(AuditEvent, User.email)
        .outerjoin(User, User.id == AuditEvent.user_id)
        .where(*filtro)
        .order_by(AuditEvent.ts.desc(), AuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [
        EventoOut.model_validate({**_colunas(ev), "user_email": email}) for ev, email in linhas.all()
    ]
    return PaginaEventos(items=items, total=total or 0, limit=limit, offset=offset)


def _colunas(ev: AuditEvent) -> dict[str, Any]:
    return {c.key: getattr(ev, c.key) for c in AuditEvent.__table__.columns}


@router.get("/api/audit/tipos")
async def tipos_de_evento(session: Sessao, user: Annotated[User, Depends(current_user)]) -> list[str]:
    """Tipos de evento visíveis para o Usuário, para o filtro da tela."""
    q = select(AuditEvent.event_type).where(*_escopo(user, None)).distinct().order_by(AuditEvent.event_type)
    return list((await session.scalars(q)).all())


class UsuarioAdmin(BaseModel):
    id: uuid.UUID
    email: str
    is_superuser: bool
    gasto_micro_usd: int
    cap_micro_usd: int


@router.get("/api/admin/usuarios")
async def usuarios(session: Sessao, _admin: Annotated[User, Depends(current_superuser)]) -> list[UsuarioAdmin]:
    """Usuários com gasto e Cap, do que mais gastou para o que menos gastou. Só admin."""
    gasto = func.coalesce(func.sum(CreditLedger.cost_micro_usd), 0)
    linhas = await session.execute(
        select(User, gasto)
        .outerjoin(CreditLedger, CreditLedger.user_id == User.id)
        .group_by(User.id)
        .order_by(gasto.desc(), User.email)
    )
    return [
        UsuarioAdmin(
            id=u.id, email=u.email, is_superuser=u.is_superuser, gasto_micro_usd=g, cap_micro_usd=await _cap(session, u.id)
        )
        for u, g in linhas.all()
    ]
