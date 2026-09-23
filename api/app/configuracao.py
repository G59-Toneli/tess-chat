"""Configuração por Usuário e por Conversa. Conversa sobrepõe Usuário, que sobrepõe o default do .env (ticket 14)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, DateTime, ForeignKey, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.auth import User, current_superuser, current_user
from app.config import settings
from app.conversas import Sessao, Usuario, conversa_do_usuario
from app.credito import Cap, _cap
from app.db import Base, get_session

# Só modelos com linha na Tabela de Preço. O 3.7 é reserva do fallback (ADR 0012), não escolha do Usuário.
Modelo = Literal["gemini-3.8-flash", "gemini-3.1-flash-lite"]
MODELO_PADRAO: Modelo = "gemini-3.8-flash"
Nivel = Literal["minimal", "low", "medium", "high"]
# Low: o default do modelo deu ~7 s até o primeiro token no spike.
NIVEL_PADRAO: Nivel = "low"


class Setting(Base):
    """Linha de Configuração de um escopo. Coluna nula herda do escopo de cima."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    modelo: Mapped[str | None]
    nivel_raciocinio: Mapped[str | None]
    compactacao_limiar: Mapped[int | None]
    roteador_limiar: Mapped[float | None]
    tool_calls_limite: Mapped[int | None]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Configuracao(BaseModel):
    """Valores que valem no turno, já resolvidos."""

    modelo: Modelo
    nivel_raciocinio: Nivel
    compactacao_limiar: int
    roteador_limiar: float
    tool_calls_limite: int


class ConfiguracaoIn(BaseModel):
    """Corpo parcial. Campo ausente não muda; `null` apaga o valor próprio e volta a herdar."""

    modelo: Modelo | None = None
    nivel_raciocinio: Nivel | None = None
    compactacao_limiar: int | None = Field(None, ge=1, le=1_000_000)
    roteador_limiar: float | None = Field(None, ge=0, le=1)
    tool_calls_limite: int | None = Field(None, ge=1, le=50)


class ConfiguracaoOut(BaseModel):
    valores: ConfiguracaoIn
    herdada: Configuracao
    efetiva: Configuracao


CAMPOS = tuple(Configuracao.model_fields)


def _padrao() -> dict[str, Any]:
    # Lido a cada chamada: os testes trocam `settings` com monkeypatch.
    return {
        "modelo": MODELO_PADRAO,
        "nivel_raciocinio": NIVEL_PADRAO,
        "compactacao_limiar": settings.compactacao_limiar,
        "roteador_limiar": settings.roteador_limiar,
        "tool_calls_limite": settings.tool_calls_limit,
    }


def _sobrepor(base: dict[str, Any], linha: Setting | None) -> dict[str, Any]:
    if linha is None:
        return base
    return {c: v if (v := getattr(linha, c)) is not None else base[c] for c in CAMPOS}


async def _linha(session: AsyncSession, *, user_id: uuid.UUID | None = None, cid: uuid.UUID | None = None) -> Setting | None:
    q = select(Setting).where(Setting.user_id == user_id) if user_id else select(Setting).where(Setting.conversation_id == cid)
    return await session.scalar(q)


# REVISAR(human): herança campo a campo. Default do .env, depois a linha do Usuário, depois a da Conversa.
# Devolve também o que a Conversa herdaria sem valor próprio: a tela mostra "herdado: X".
async def resolver(session: AsyncSession, user_id: uuid.UUID, cid: uuid.UUID | None) -> tuple[Configuracao, Configuracao]:
    herdada = _sobrepor(_padrao(), await _linha(session, user_id=user_id)) if cid else _padrao()
    propria = await _linha(session, cid=cid) if cid else await _linha(session, user_id=user_id)
    return Configuracao(**herdada), Configuracao(**_sobrepor(herdada, propria))


async def configuracao_do_turno(
    cid: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
) -> Configuracao:
    """Dependência do chat. A posse da Conversa é checada no endpoint."""
    return (await resolver(session, user.id, cid))[1]


async def _saida(session: AsyncSession, user_id: uuid.UUID, cid: uuid.UUID | None) -> ConfiguracaoOut:
    linha = await _linha(session, cid=cid) if cid else await _linha(session, user_id=user_id)
    herdada, efetiva = await resolver(session, user_id, cid)
    valores = ConfiguracaoIn(**{c: getattr(linha, c) for c in CAMPOS}) if linha else ConfiguracaoIn()
    return ConfiguracaoOut(valores=valores, herdada=herdada, efetiva=efetiva)


async def _salvar(session: AsyncSession, user: User, cid: uuid.UUID | None, body: ConfiguracaoIn) -> ConfiguracaoOut:
    """Grava os campos enviados e emite `settings_changed` só com o que mudou."""
    linha = await _linha(session, cid=cid) if cid else await _linha(session, user_id=user.id)
    if linha is None:
        linha = Setting(user_id=None if cid else user.id, conversation_id=cid)
        session.add(linha)
    alteracoes = {}
    for campo, novo in body.model_dump(exclude_unset=True).items():
        antigo = getattr(linha, campo)
        if antigo != novo:
            alteracoes[campo] = {"de": antigo, "para": novo}
            setattr(linha, campo, novo)
    if alteracoes:
        linha.updated_at = func.now()
        escopo = "conversa" if cid else "usuario"
        await audit(
            session, "settings_changed", user_id=user.id, conversation_id=cid,
            payload={"escopo": escopo, "alteracoes": alteracoes},
        )
    await session.commit()
    return await _saida(session, user.id, cid)


router = APIRouter(tags=["configuracao"])


@router.get("/api/settings")
async def do_usuario(session: Sessao, user: Usuario) -> ConfiguracaoOut:
    """Configuração do Usuário logado: valores próprios e efetivos."""
    return await _saida(session, user.id, None)


@router.put("/api/settings")
async def salvar_do_usuario(body: ConfiguracaoIn, session: Sessao, user: Usuario) -> ConfiguracaoOut:
    return await _salvar(session, user, None, body)


@router.get("/api/conversations/{cid}/settings")
async def da_conversa(cid: uuid.UUID, session: Sessao, user: Usuario) -> ConfiguracaoOut:
    """Configuração da Conversa: valores próprios, o que herda do Usuário e o efetivo."""
    await conversa_do_usuario(session, user, cid)
    return await _saida(session, user.id, cid)


@router.put("/api/conversations/{cid}/settings")
async def salvar_da_conversa(cid: uuid.UUID, body: ConfiguracaoIn, session: Sessao, user: Usuario) -> ConfiguracaoOut:
    await conversa_do_usuario(session, user, cid)
    return await _salvar(session, user, cid, body)


class CapIn(BaseModel):
    cap_micro_usd: int = Field(ge=0)


class CapOut(BaseModel):
    user_id: uuid.UUID
    cap_micro_usd: int


@router.put("/api/admin/usuarios/{uid}/cap")
async def definir_cap(
    uid: uuid.UUID, body: CapIn, session: Sessao, admin: Annotated[User, Depends(current_superuser)]
) -> CapOut:
    """Cap de Crédito de um Usuário. Só admin. Grava em `caps`, que o Crédito já lê."""
    if await session.get(User, uid) is None:
        raise HTTPException(status_code=404, detail="Usuário inexistente")
    antigo = await _cap(session, uid)
    q = insert(Cap).values(user_id=uid, limite_micro_usd=body.cap_micro_usd)
    await session.execute(q.on_conflict_do_update(index_elements=["user_id"], set_={"limite_micro_usd": body.cap_micro_usd}))
    if antigo != body.cap_micro_usd:
        await audit(
            session, "settings_changed", user_id=admin.id,
            payload={
                "escopo": "cap",
                "usuario_alvo": str(uid),
                "alteracoes": {"cap_micro_usd": {"de": antigo, "para": body.cap_micro_usd}},
            },
        )
    await session.commit()
    return CapOut(user_id=uid, cap_micro_usd=body.cap_micro_usd)
