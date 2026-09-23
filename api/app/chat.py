"""Chat com streaming: histórico do banco, Agent do Pydantic AI, protocolo do AI SDK (ADR 0001, 0003)."""

import time
import uuid
from collections.abc import AsyncIterator
from functools import cache
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import FileUIPart, TextUIPart, UIMessage
from pydantic_ai.usage import RunUsage
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

from app.audit import audit
from app.auth import User, current_user
from app.config import settings
from app.conversas import Conversation, Message, conversa_do_usuario
from app.credito import acertar, reservar
from app.db import SessionLocal, get_session
from app.roteador import PRECO_JEV, Gate, apply_gate, cliente_jev, decidir, opcoes
from app.tools import estado_da_conversa, toolset_da_conversa, transporte

MODELO = "gemini-3.8-flash"
# Thinking explícito. O default do modelo deu ~7 s até o primeiro token no spike.
AJUSTES = GoogleModelSettings(
    google_thinking_config={"thinking_level": "low"}, max_tokens=settings.max_output_tokens
)
SDK = 7

agent = Agent(retries=0)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@cache
def _gemini() -> GoogleModel:
    return GoogleModel(MODELO, provider=GoogleProvider(api_key=settings.gemini_paid_api_key))


def modelo() -> Model:
    """Modelo da rota. Os testes trocam via dependency_overrides."""
    return _gemini()


def _historico(linhas: list[Message]):
    """Mensagens do banco (partes do AI SDK) para mensagens do Pydantic AI."""
    ui = [UIMessage(id=str(m.id), role=m.role, parts=m.parts) for m in linhas]
    return VercelAIAdapter.load_messages(ui)


# REVISAR(human): estimativa local de input para a reserva, sem chamar countTokens.
# ~3 caracteres por token sobre o JSON das partes: conservador para pt-BR (INFERIDO).
def _estimar_input(linhas: list[Message], novas: list[Any]) -> int:
    chars = sum(len(str(m.parts)) for m in linhas) + sum(len(str(n.model_dump())) for n in novas)
    return -(-chars // 3)


async def _erro(cid: uuid.UUID, uid: uuid.UUID, nome: str, exc: Exception, t0: float) -> None:
    async with SessionLocal() as s:
        await audit(
            s,
            "llm_error",
            user_id=uid,
            conversation_id=cid,
            model=nome,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            payload={"erro": type(exc).__name__, "status": getattr(exc, "status_code", None), "msg": str(exc)[:500]},
        )
        await s.commit()


async def _rotear(
    session: AsyncSession, jev: AsyncTypeSafeClient | None, uid: uuid.UUID, cid: uuid.UUID, nova: UIMessage
) -> Gate:
    """Roteador antes do Gemini. Qualquer falha do Jev vira AUTO com evento router_fallback."""
    texto = "\n".join(p.text for p in nova.parts if isinstance(p, TextUIPart))
    anexos = [p.filename or p.media_type for p in nova.parts if isinstance(p, FileUIPart)]
    ativas = [(t.nome, t.descricao) for t, a in await estado_da_conversa(session, cid) if a]
    t0 = time.perf_counter()
    try:
        if jev is None:
            raise TypeSafeError("TYPESAFE_API_KEY ausente")
        d = await decidir(jev, texto, anexos, opcoes(ativas))
    except TypeSafeError as exc:
        await audit(
            session,
            "router_fallback",
            user_id=uid,
            conversation_id=cid,
            model=PRECO_JEV,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            payload={"erro": type(exc).__name__, "status": getattr(exc, "status", None), "msg": str(exc)[:500]},
        )
        return Gate(None)
    escolha = apply_gate(d, settings.roteador_limiar)
    uso = RunUsage(input_tokens=d.input_tokens, output_tokens=d.output_tokens)
    custo = await acertar(session, uid, cid, None, PRECO_JEV, uso)
    await audit(
        session,
        "router_decision",
        user_id=uid,
        conversation_id=cid,
        model=PRECO_JEV,
        input_tokens=d.input_tokens,
        output_tokens=d.output_tokens,
        cost_micro_usd=custo,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        payload={
            "tool": d.tool,
            "confidence": d.confidence,
            "distribution": d.distribution,
            "limiar": settings.roteador_limiar,
            "forcada": escolha is not None,
            "modelo_real": d.modelo,
        },
    )
    return Gate(escolha)


# REVISAR(human): grava usuário e assistente juntos, só no fim do turno com sucesso.
# Turno que falha não deixa mensagem órfã no histórico. Uso vai na mensagem do assistente.
async def _persistir(
    cid: uuid.UUID, uid: uuid.UUID, nome: str, result: AgentRunResult[Any], antes: int, t0: float
) -> None:
    latencia = int((time.perf_counter() - t0) * 1000)
    uso = result.usage
    # new_messages() não traz a mensagem do front: o adapter a põe no message_history.
    ui = VercelAIAdapter.dump_messages(result.all_messages()[antes:], sdk_version=SDK)
    async with SessionLocal() as s:
        linhas = [
            Message(conversation_id=cid, role=m.role, parts=[p.model_dump(mode="json", by_alias=True) for p in m.parts])
            for m in ui
        ]
        ultima = next(m for m in reversed(linhas) if m.role == "assistant")
        ultima.model = nome
        ultima.input_tokens = uso.input_tokens
        ultima.output_tokens = uso.output_tokens  # já inclui thinking
        ultima.thinking_tokens = uso.details.get("thoughts_tokens")
        ultima.cache_read_tokens = uso.cache_read_tokens
        s.add_all(linhas)
        await s.flush()
        conv = await s.get(Conversation, cid)
        conv.updated_at = func.now()
        custo = await acertar(s, uid, cid, ultima.id, nome, uso)
        await audit(s, "message_sent", user_id=uid, conversation_id=cid, payload={"message_id": linhas[0].id})
        await audit(
            s,
            "llm_call",
            user_id=uid,
            conversation_id=cid,
            model=nome,
            input_tokens=uso.input_tokens,
            output_tokens=uso.output_tokens,
            cost_micro_usd=custo,
            latency_ms=latencia,
            payload={
                "thinking_tokens": uso.details.get("thoughts_tokens"),
                "cache_read_tokens": uso.cache_read_tokens,
                "requests": uso.requests,
                "message_id": ultima.id,
            },
        )
        await s.commit()


# REVISAR(human): 502 só quando o provedor falha antes do primeiro evento.
# Depois que o stream começou o status 200 já foi, então o erro vai como chunk de erro do AI SDK.
# Nos dois casos grava llm_error.
@router.post("/{cid}")
async def chat(
    cid: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
    m: Annotated[Model, Depends(modelo)],
    t: Annotated[httpx.AsyncBaseTransport | None, Depends(transporte)],
    jev: Annotated[AsyncTypeSafeClient | None, Depends(cliente_jev)],
) -> Response:
    """Roda um turno da Conversa e devolve o stream no protocolo do AI SDK."""
    await conversa_do_usuario(session, user, cid)
    try:
        adapter = await VercelAIAdapter.from_request(request, agent=agent, sdk_version=SDK)
    except ValidationError as e:
        return Response(e.json(include_input=False), status_code=422, media_type="application/json")
    # O histórico vem do banco. Do front só vale a mensagem nova.
    novas = adapter.run_input.messages[-1:]
    if not novas or novas[0].role != "user":
        raise HTTPException(status_code=422, detail="A última mensagem precisa ser do usuário")
    adapter.run_input.messages = novas

    q = select(Message).where(Message.conversation_id == cid).order_by(Message.created_at, Message.id)
    linhas = list((await session.scalars(q)).all())
    historico = _historico(linhas)
    uid, nome = user.id, m.model_name
    await reservar(session, uid, cid, nome, _estimar_input(linhas, novas))
    tools = await toolset_da_conversa(session, uid, cid, t)
    gate = await _rotear(session, jev, uid, cid, novas[0])
    await session.commit()
    await session.close()

    t0 = time.perf_counter()

    async def eventos() -> AsyncIterator[Any]:
        try:
            async for ev in adapter.run_stream_native(
                message_history=historico, model=m, model_settings=AJUSTES, conversation_id=str(cid),
                toolsets=[tools], capabilities=[gate],
            ):
                yield ev
        except ModelAPIError as exc:
            await _erro(cid, uid, nome, exc, t0)
            raise

    nativos = eventos()
    try:
        primeiro = await anext(nativos)
    except ModelAPIError as exc:
        status = f"HTTP {exc.status_code}" if isinstance(exc, ModelHTTPError) else type(exc).__name__
        return JSONResponse({"detail": f"O provedor do modelo falhou ({status}). Tente de novo."}, status_code=502)

    async def todos() -> AsyncIterator[Any]:
        yield primeiro
        async for ev in nativos:
            yield ev

    async def ao_fim(result: AgentRunResult[Any]) -> None:
        await _persistir(cid, uid, nome, result, len(historico), t0)

    return adapter.streaming_response(adapter.transform_stream(todos(), on_complete=ao_fim))
