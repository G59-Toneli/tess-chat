"""Crédito em micro-USD: Tabela de Preço, Ledger, Cap, reserva e acerto (ADR 0004)."""

import uuid
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic_ai.usage import RunUsage
from sqlalchemy import BigInteger, DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.auth import User, current_superuser, current_user
from app.config import settings
from app.conversas import conversa_do_usuario
from app.db import Base, SessionLocal, get_session
from app.roteador import PRECO_JEV

MILHAO = 1_000_000


# Erros de domínio sem HTTP: preco_vigente também roda dentro do stream (acerto, Compactação),
# onde não existe status para devolver. A borda HTTP traduz em main.py (402 e 500).
class CapAtingido(Exception):
    """Reserva passa do Cap. A mensagem é o `detail` do 402."""


class PrecoAusente(Exception):
    """Modelo sem linha na Tabela de Preço: erro de configuração. A mensagem é o `detail` do 500."""


class PrecoModelo(Base):
    """Linha da Tabela de Preço. Micro-USD por 1M de tokens."""

    __tablename__ = "price_table"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model: Mapped[str]
    input_micro_usd_1m: Mapped[int] = mapped_column(BigInteger)
    output_micro_usd_1m: Mapped[int] = mapped_column(BigInteger)
    cache_micro_usd_1m: Mapped[int] = mapped_column(BigInteger)
    thinking_micro_usd_1m: Mapped[int] = mapped_column(BigInteger)
    # Só a Ligação (migração 0024). Nulo nos modelos de texto.
    audio_input_micro_usd_1m: Mapped[int | None] = mapped_column(BigInteger)
    image_input_micro_usd_1m: Mapped[int | None] = mapped_column(BigInteger)
    audio_output_micro_usd_1m: Mapped[int | None] = mapped_column(BigInteger)
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CreditLedger(Base):
    """Um débito por chamada ao modelo. Somente-inserção."""

    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[uuid.UUID]
    conversation_id: Mapped[uuid.UUID | None]
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    model: Mapped[str]
    price_id: Mapped[int] = mapped_column(BigInteger)
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]  # já inclui thinking
    thinking_tokens: Mapped[int]
    cache_read_tokens: Mapped[int]
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger)


class Cap(Base):
    """Limite de Crédito. `user_id` nulo é o Cap global."""

    __tablename__ = "caps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID | None]
    limite_micro_usd: Mapped[int] = mapped_column(BigInteger)


# custo real de uma chamada em micro-USD inteiro.
# promptTokenCount do Gemini já inclui o cache: input cobrado = input - cache.
# output_tokens já inclui thinking: thinking sai do output e vai ao preço de thinking.
# Uma divisão só no total, arredondada para cima: nunca cobra menos que o provedor.
def debit(usage: RunUsage, price: PrecoModelo) -> int:
    cache = usage.cache_read_tokens
    thinking = usage.details.get("thoughts_tokens", 0)
    total = (
        (usage.input_tokens - cache) * price.input_micro_usd_1m
        + cache * price.cache_micro_usd_1m
        + (usage.output_tokens - thinking) * price.output_micro_usd_1m
        + thinking * price.thinking_micro_usd_1m
    )
    return -(-total // MILHAO)


async def preco_vigente(session: AsyncSession, model: str) -> PrecoModelo:
    """Preço com a maior vigência já iniciada. Modelo sem preço é erro de configuração."""
    q = (
        select(PrecoModelo)
        .where(PrecoModelo.model == model, PrecoModelo.vigente_desde <= func.now())
        .order_by(PrecoModelo.vigente_desde.desc())
        .limit(1)
    )
    preco = await session.scalar(q)
    if preco is None:
        raise PrecoAusente(f"Modelo sem preço na Tabela de Preço: {model}")
    return preco


async def _gasto(session: AsyncSession, user_id: uuid.UUID | None) -> int:
    q = select(func.coalesce(func.sum(CreditLedger.cost_micro_usd), 0))
    if user_id is not None:
        q = q.where(CreditLedger.user_id == user_id)
    return int(await session.scalar(q))


async def _cap(session: AsyncSession, user_id: uuid.UUID | None) -> int:
    q = select(Cap.limite_micro_usd).where(
        Cap.user_id == user_id if user_id is not None else Cap.user_id.is_(None)
    )
    limite = await session.scalar(q)
    if limite is not None:
        return limite
    return settings.cap_usuario_micro_usd if user_id is not None else settings.cap_global_micro_usd


# reserva = custo do input estimado + max_tokens inteiro de saída ao preço de output.
# Recusa se a reserva passa do que falta no Cap do Usuário ou no global. Não grava a reserva:
# o Ledger só recebe o acerto real. Duas chamadas simultâneas podem passar juntas (ressalva).
async def reservar(
    session: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, model: str, input_estimado: int
) -> PrecoModelo:
    """Garante que a chamada cabe nos Caps. Recusa com CapAtingido e evento `cap_reached`."""
    preco = await preco_vigente(session, model)
    reserva = debit(RunUsage(input_tokens=input_estimado, output_tokens=settings.max_output_tokens), preco)
    await caber(session, user_id, conversation_id, model, reserva)
    return preco


async def caber(
    session: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, model: str, reserva: int
) -> None:
    """Recusa com CapAtingido e evento `cap_reached` se a reserva passa do Cap do Usuário ou do global."""
    for escopo, uid in (("usuario", user_id), ("global", None)):
        gasto, cap = await _gasto(session, uid), await _cap(session, uid)
        if gasto + reserva > cap:
            async with SessionLocal() as s:
                await audit(
                    s,
                    "cap_reached",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    model=model,
                    cost_micro_usd=reserva,
                    payload={"escopo": escopo, "gasto": gasto, "reserva": reserva, "cap": cap},
                )
                await s.commit()
            raise CapAtingido(f"Cap de crédito atingido ({escopo}).")


async def acertar(
    session: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: int | None,
    model: str,
    usage: RunUsage,
) -> int:
    """Grava no Ledger o custo real com o preço vigente agora. Quem chama faz o commit."""
    preco = await preco_vigente(session, model)
    custo = debit(usage, preco)
    session.add(
        CreditLedger(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            model=model,
            price_id=preco.id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            thinking_tokens=usage.details.get("thoughts_tokens", 0),
            cache_read_tokens=usage.cache_read_tokens,
            cost_micro_usd=custo,
        )
    )
    return custo


class Saldo(BaseModel):
    gasto_micro_usd: int
    cap_micro_usd: int
    saldo_micro_usd: int


router = APIRouter(prefix="/api/credits", tags=["credits"])


async def _saldo(session: AsyncSession, user_id: uuid.UUID | None) -> Saldo:
    gasto, cap = await _gasto(session, user_id), await _cap(session, user_id)
    return Saldo(gasto_micro_usd=gasto, cap_micro_usd=cap, saldo_micro_usd=cap - gasto)


@router.get("/me")
async def meu_credito(
    session: Annotated[AsyncSession, Depends(get_session)], user: Annotated[User, Depends(current_user)]
) -> Saldo:
    """Gasto, Cap e saldo do Usuário logado."""
    return await _saldo(session, user.id)


@router.get("/global")
async def credito_global(
    session: Annotated[AsyncSession, Depends(get_session)], _user: Annotated[User, Depends(current_user)]
) -> Saldo:
    """Gasto, Cap e saldo somados de todos os Usuários."""
    return await _saldo(session, None)


class GastoDia(BaseModel):
    dia: date
    custo_micro_usd: int


class GastoModelo(BaseModel):
    model: str
    custo_micro_usd: int
    chamadas: int


class LinhaLedger(BaseModel):
    id: int
    ts: datetime
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None
    model: str
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    cache_read_tokens: int
    cost_micro_usd: int


class Painel(BaseModel):
    saldo: Saldo
    por_dia: list[GastoDia]
    por_modelo: list[GastoModelo]
    ultimas: list[LinhaLedger]


def _fuso(tz: str = "UTC") -> str:
    """Fuso IANA do browser. Inválido é 422 antes de chegar ao Postgres."""
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail=f"Fuso inválido: {tz}") from None
    return tz


Fuso = Annotated[str, Depends(_fuso)]


# dia do gasto no fuso do browser (UI-GUIA), não em UTC:
# 22h em Brasília já é o dia seguinte em UTC. Últimas 20 linhas do Ledger.
async def _painel(session: AsyncSession, user_id: uuid.UUID | None, tz: str) -> Painel:
    filtro = [CreditLedger.user_id == user_id] if user_id is not None else []
    custo = func.sum(CreditLedger.cost_micro_usd)
    dia = func.date(func.timezone(tz, CreditLedger.ts)).label("dia")
    por_dia = await session.execute(select(dia, custo).where(*filtro).group_by(dia).order_by(dia))
    por_modelo = await session.execute(
        select(CreditLedger.model, custo, func.count())
        .where(*filtro)
        .group_by(CreditLedger.model)
        .order_by(custo.desc())
    )
    ultimas = await session.scalars(select(CreditLedger).where(*filtro).order_by(CreditLedger.id.desc()).limit(20))
    return Painel(
        saldo=await _saldo(session, user_id),
        por_dia=[GastoDia(dia=d, custo_micro_usd=c) for d, c in por_dia.all()],
        por_modelo=[GastoModelo(model=m, custo_micro_usd=c, chamadas=n) for m, c, n in por_modelo.all()],
        ultimas=[LinhaLedger.model_validate(linha, from_attributes=True) for linha in ultimas.all()],
    )


@router.get("/me/painel")
async def meu_painel(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    tz: Fuso,
) -> Painel:
    """Saldo, gasto por dia e por modelo e últimas linhas do Ledger do Usuário logado."""
    return await _painel(session, user.id, tz)


@router.get("/global/painel")
async def painel_global(
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(current_superuser)],
    tz: Fuso,
) -> Painel:
    """O mesmo painel somando todos os Usuários, contra o Cap global. Só admin."""
    return await _painel(session, None, tz)


class GastoOrigem(BaseModel):
    origem: str  # resposta | roteador | compactacao
    custo_micro_usd: int
    chamadas: int


class CustoConversa(BaseModel):
    total_micro_usd: int
    chamadas: int
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    cache_read_tokens: int
    por_origem: list[GastoOrigem]
    saldo: Saldo


# a origem sai da linha do Ledger, sem coluna nova. Linha com message_id é a
# resposta do modelo de chat; sem message_id, o modelo do Jev é o Roteador e o resto é a
# Compactação (os dois únicos acertos sem Mensagem, ver chat.py e compactacao.py).
@router.get("/conversas/{cid}")
async def custo_da_conversa(
    cid: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
) -> CustoConversa:
    """Soma do Ledger de uma Conversa do Usuário, por origem, com o saldo dele ao lado."""
    await conversa_do_usuario(session, user, cid)
    linhas = (await session.scalars(select(CreditLedger).where(CreditLedger.conversation_id == cid))).all()
    origens: dict[str, list[int]] = {}
    for linha in linhas:
        origem = "resposta" if linha.message_id else "roteador" if linha.model == PRECO_JEV else "compactacao"
        par = origens.setdefault(origem, [0, 0])
        par[0] += linha.cost_micro_usd
        par[1] += 1
    return CustoConversa(
        total_micro_usd=sum(linha.cost_micro_usd for linha in linhas),
        chamadas=len(linhas),
        input_tokens=sum(linha.input_tokens for linha in linhas),
        output_tokens=sum(linha.output_tokens for linha in linhas),
        thinking_tokens=sum(linha.thinking_tokens for linha in linhas),
        cache_read_tokens=sum(linha.cache_read_tokens for linha in linhas),
        por_origem=sorted(
            (GastoOrigem(origem=o, custo_micro_usd=c, chamadas=n) for o, (c, n) in origens.items()),
            key=lambda g: -g.custo_micro_usd,
        ),
        saldo=await _saldo(session, user.id),
    )
