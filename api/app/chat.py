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
from pydantic_ai.messages import ModelResponse, PartDeltaEvent, PartStartEvent
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import FileUIPart, TextUIPart, UIMessage
from pydantic_ai.usage import RunUsage, UsageLimits
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

from app.anexos import montar_anexos
from app.audit import audit
from app.compactacao import Compactacao, com_resumo, modelo_resumo, ponto_de_corte, should_compact, ultimo_resumo
from app.auth import User, current_user
from app.config import settings
from app.configuracao import MODELO_PADRAO, Configuracao, configuracao_do_turno
from app.conversas import Conversation, Message, conversa_do_usuario
from app.credito import acertar, reservar
from app.db import SessionLocal, get_session
from app.resiliencia import ERROS_PROVEDOR, Turno, cadeia, causa, resumo_erro
from app.roteador import PRECO_JEV, Gate, apply_gate, cliente_jev, decidir, opcoes
from app.tools import estado_da_conversa, toolset_da_conversa, transporte

MODELO = MODELO_PADRAO
# Fallback do ADR 0012. Sem OPENAI_API_KEY no .env, a cadeia para aqui.
MODELO_RESERVA = "gemini-3.7-flash"
SDK = 7

agent = Agent(retries=0)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@cache
def _gemini(nome: str = MODELO) -> GoogleModel:
    return GoogleModel(nome, provider=GoogleProvider(api_key=settings.gemini_paid_api_key))


def modelo(cfg: Annotated[Configuracao, Depends(configuracao_do_turno)]) -> Model:
    """Modelo da Configuração do turno. Os testes trocam via dependency_overrides."""
    return _gemini(cfg.modelo)


def ajustes(cfg: Configuracao) -> GoogleModelSettings:
    """Thinking explícito, nível vindo da Configuração."""
    return GoogleModelSettings(
        google_thinking_config={"thinking_level": cfg.nivel_raciocinio}, max_tokens=settings.max_output_tokens
    )


def modelo_reserva() -> Model | None:
    """Próximo da cadeia de fallback. None desliga o fallback (testes)."""
    return _gemini(MODELO_RESERVA)


def _historico(linhas: list[Message]):
    """Mensagens do banco (partes do AI SDK) para mensagens do Pydantic AI."""
    ui = [UIMessage(id=str(m.id), role=m.role, parts=m.parts) for m in linhas]
    return VercelAIAdapter.load_messages(ui)


# REVISAR(human): estimativa local de input para a reserva, sem chamar countTokens.
# ~3 caracteres por token sobre o JSON das partes: conservador para pt-BR (INFERIDO).
def _estimar_input(linhas: list[Message], novas: list[Any]) -> int:
    chars = sum(len(str(m.parts)) for m in linhas) + sum(len(str(n.model_dump())) for n in novas)
    return -(-chars // 3)


async def _auditar_tentativas(s: AsyncSession, uid: uuid.UUID, cid: uuid.UUID, turno: Turno) -> None:
    """Um `llm_retry` por tentativa que falhou e um `llm_fallback` por troca de modelo."""
    for r in turno.retries:
        await audit(s, "llm_retry", user_id=uid, conversation_id=cid, model=r["modelo"], payload=r)
    for f in turno.fallbacks:
        await audit(s, "llm_fallback", user_id=uid, conversation_id=cid, model=f["para"], payload=f)


async def _erro(
    cid: uuid.UUID, uid: uuid.UUID, nome: str, exc: BaseException, turno: Turno, comp: Compactacao | None = None
) -> None:
    async with SessionLocal() as s:
        if comp:
            await comp.auditar(s, None)
        await _auditar_tentativas(s, uid, cid, turno)
        await audit(
            s,
            "llm_error",
            user_id=uid,
            conversation_id=cid,
            model=nome,
            latency_ms=int((time.perf_counter() - turno.t0) * 1000),
            payload={**resumo_erro(exc), "tentativas": turno.tentativas},
        )
        await s.commit()


async def _limite_de_tools(
    cid: uuid.UUID, uid: uuid.UUID, nome: str, exc: UsageLimitExceeded, turno: Turno, comp: Compactacao | None
) -> None:
    async with SessionLocal() as s:
        if comp:
            await comp.auditar(s, None)
        await _auditar_tentativas(s, uid, cid, turno)
        await audit(
            s,
            "tool_limit_reached",
            user_id=uid,
            conversation_id=cid,
            model=turno.respondido or nome,
            latency_ms=int((time.perf_counter() - turno.t0) * 1000),
            payload={"limite": settings.tool_calls_limit, "msg": str(exc)[:500]},
        )
        await s.commit()


async def _rotear(
    session: AsyncSession,
    jev: AsyncTypeSafeClient | None,
    uid: uuid.UUID,
    cid: uuid.UUID,
    nova: UIMessage,
    limiar: float,
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
    escolha = apply_gate(d, limiar)
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
            "limiar": limiar,
            "forcada": escolha is not None,
            "modelo_real": d.modelo,
        },
    )
    return Gate(escolha)


# REVISAR(human): grava usuário e assistente juntos, só no fim do turno com sucesso.
# Turno que falha não deixa mensagem órfã no histórico. Uso vai na mensagem do assistente.
async def _persistir(
    cid: uuid.UUID,
    uid: uuid.UUID,
    turno: Turno,
    result: AgentRunResult[Any],
    antes: int,
    comp: Compactacao | None = None,
) -> None:
    latencia = int((time.perf_counter() - turno.t0) * 1000)
    uso = result.usage
    # Mensagem e Ledger levam o modelo que respondeu, com o preço dele.
    nome = turno.respondido or turno.pedido
    resposta = result.response
    # new_messages() não traz a mensagem do front: o adapter a põe no message_history.
    # A Compactação encolhe o histórico do run: o índice das novas desloca junto.
    novas = result.all_messages()[antes - (comp.removidos if comp else 0) :]
    ui = VercelAIAdapter.dump_messages(novas, sdk_version=SDK)
    async with SessionLocal() as s:
        if comp:
            primeira = next((m for m in novas if isinstance(m, ModelResponse)), None)
            await comp.auditar(s, primeira.usage.input_tokens if primeira else None)
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
        await _auditar_tentativas(s, uid, cid, turno)
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
                "modelo_pedido": turno.pedido,
                "modelo_respondido": nome,
                "modelo_real": resposta.model_name,
                "tentativas": turno.tentativas,
                "latencia_primeiro_token_ms": turno.primeiro_token_ms,
                "motivo_termino": resposta.finish_reason,
            },
        )
        await s.commit()


async def _preparar_historico(
    session: AsyncSession, uid: uuid.UUID, cid: uuid.UUID, linhas: list[Message], mr: Model, cfg: Configuracao
) -> tuple[list[Any], Compactacao | None]:
    """Resumo vigente + Mensagens depois do corte. Monta a Compactação se o turno anterior passou do limiar."""
    resumo = await ultimo_resumo(session, cid)
    efetivas = [l for l in linhas if resumo is None or l.id > resumo.ate_message_id]
    texto = resumo.texto if resumo else None
    historico = com_resumo(texto, _historico(efetivas))
    anterior = next((l for l in reversed(efetivas) if l.role == "assistant"), None)
    uso = RunUsage(input_tokens=anterior.input_tokens or 0) if anterior else None
    corte = ponto_de_corte([l.role for l in efetivas], settings.compactacao_turnos_literais)
    if corte is None or not should_compact(uso, cfg):
        return historico, None
    comp = Compactacao(
        uid=uid,
        cid=cid,
        modelo=mr,
        resumo_anterior=texto,
        antigas=_historico(efetivas[:corte]),
        recentes=_historico(efetivas[corte:]),
        ate_message_id=efetivas[corte - 1].id,
        tokens_antes=uso.input_tokens,
        tamanho_historico=len(historico),
    )
    return historico, comp


@router.get("/{cid}/compactacao")
async def corte_atual(
    cid: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
) -> dict[str, int | None]:
    """Última Mensagem coberta pelo Resumo vigente. O front marca \"histórico compactado aqui\" depois dela."""
    await conversa_do_usuario(session, user, cid)
    resumo = await ultimo_resumo(session, cid)
    return {"ate_message_id": resumo.ate_message_id if resumo else None}


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
    reserva: Annotated[Model | None, Depends(modelo_reserva)],
    mr: Annotated[Model, Depends(modelo_resumo)],
    t: Annotated[httpx.AsyncBaseTransport | None, Depends(transporte)],
    jev: Annotated[AsyncTypeSafeClient | None, Depends(cliente_jev)],
    cfg: Annotated[Configuracao, Depends(configuracao_do_turno)],
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
    uid, nome = user.id, m.model_name
    historico, comp = await _preparar_historico(session, uid, cid, linhas, mr, cfg)
    await reservar(session, uid, cid, nome, _estimar_input(linhas, novas))
    tools = await toolset_da_conversa(session, uid, cid, t)
    gate = await _rotear(session, jev, uid, cid, novas[0], cfg.roteador_limiar)
    # Depois da reserva e do Roteador: o base64 não entra na estimativa nem no Jev.
    await montar_anexos(session, uid, novas[0])
    await session.commit()
    await session.close()

    turno = Turno(nome)
    modelos = cadeia(turno, [m, *([reserva] if reserva else [])])
    limites = UsageLimits(tool_calls_limit=settings.tool_calls_limit)

    async def eventos() -> AsyncIterator[Any]:
        try:
            async for ev in adapter.run_stream_native(
                message_history=historico, model=modelos, model_settings=ajustes(cfg), conversation_id=str(cid),
                toolsets=[tools], capabilities=[gate, *([comp.capability()] if comp else [])],
                usage_limits=limites,
            ):
                if isinstance(ev, (PartStartEvent, PartDeltaEvent)):
                    turno.marcar_primeiro_token()
                yield ev
        except UsageLimitExceeded as exc:
            await _limite_de_tools(cid, uid, nome, exc, turno, comp)
            raise
        except ERROS_PROVEDOR as exc:
            await _erro(cid, uid, nome, exc, turno, comp)
            raise

    nativos = eventos()
    try:
        primeiro = await anext(nativos)
    except ERROS_PROVEDOR as exc:
        exc = causa(exc)
        status = f"HTTP {exc.status_code}" if isinstance(exc, ModelHTTPError) else type(exc).__name__
        return JSONResponse({"detail": f"O provedor do modelo falhou ({status}). Tente de novo."}, status_code=502)

    async def todos() -> AsyncIterator[Any]:
        yield primeiro
        async for ev in nativos:
            yield ev

    async def ao_fim(result: AgentRunResult[Any]) -> None:
        await _persistir(cid, uid, turno, result, len(historico), comp)

    return adapter.streaming_response(adapter.transform_stream(todos(), on_complete=ao_fim))
