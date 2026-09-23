"""Registro de Tools com toggle por Conversa, e as Tools nativas web_search e web_fetch (ADR 0009)."""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

import httpx
import trafilatura
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.toolsets import AbstractToolset, WrapperToolset
from pydantic_ai.toolsets.abstract import ToolsetTool
from sqlalchemy import Boolean, ForeignKey, Text, exists, or_, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from tavily import AsyncTavilyClient

from app import conectores
from app.audit import audit
from app.config import settings
from app.auth import User, current_superuser
from app.conversas import Conversation, Sessao, Usuario, conversa_do_usuario
from app.db import Base, SessionLocal

# Teto do texto que volta ao modelo por chamada (~6k tokens, INFERIDO).
LIMITE_CHARS = 20_000
TRECHO_BUSCA = 600
TIMEOUT = httpx.Timeout(30.0)


class Tool(Base):
    __tablename__ = "tools"

    nome: Mapped[str] = mapped_column(Text, primary_key=True)
    origem: Mapped[str] = mapped_column(Text)  # nativa | mcp
    descricao: Mapped[str] = mapped_column(Text)
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ativa_global: Mapped[bool] = mapped_column(Boolean)


class ConversationTool(Base):
    __tablename__ = "conversation_tools"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    tool_nome: Mapped[str] = mapped_column(ForeignKey("tools.nome", ondelete="CASCADE"), primary_key=True)
    ativa: Mapped[bool] = mapped_column(Boolean)


def transporte() -> httpx.AsyncBaseTransport | None:
    """Transporte HTTP das tools. None é a rede real. Os testes trocam via dependency_overrides."""
    return None


# ---------- Tools nativas ----------


async def web_search(query: str, t: httpx.AsyncBaseTransport | None = None) -> str:
    """Busca no Tavily e devolve título, URL e trecho de cada resultado."""
    if not settings.tavily_api_key:
        return "web_search indisponível: TAVILY_API_KEY ausente."
    try:
        async with httpx.AsyncClient(transport=t, timeout=TIMEOUT) as http:
            r = await AsyncTavilyClient(api_key=settings.tavily_api_key, client=http).search(query, max_results=5)
    except Exception as e:  # noqa: BLE001  erro vira texto para o modelo (Agent roda com retries=0)
        return f"web_search falhou: {type(e).__name__}"
    blocos = [
        f"[{i}] {x.get('title', '')}\nURL: {x.get('url', '')}\n{(x.get('content') or '')[:TRECHO_BUSCA]}"
        for i, x in enumerate(r.get("results", []), 1)
    ]
    return "\n\n".join(blocos) or "Nenhum resultado."


# REVISAR(human): Jina Reader primeiro; qualquer falha (status != 200, corpo vazio, erro de rede)
# cai no GET direto da URL + trafilatura. Texto cortado em LIMITE_CHARS para não estourar o contexto.
async def web_fetch(url: str, t: httpx.AsyncBaseTransport | None = None) -> str:
    """Baixa a URL e devolve o texto limpo."""
    async with httpx.AsyncClient(transport=t, timeout=TIMEOUT, follow_redirects=True) as http:
        try:
            r = await http.get(f"https://r.jina.ai/{url}")
            if r.status_code == 200 and r.text.strip():
                return r.text[:LIMITE_CHARS]
        except httpx.HTTPError:
            pass
        try:
            r = await http.get(url)
            r.raise_for_status()
        except httpx.HTTPError as e:
            return f"web_fetch falhou: {type(e).__name__}"
    texto = await asyncio.to_thread(trafilatura.extract, r.text)
    return texto[:LIMITE_CHARS] if texto else f"web_fetch: sem texto extraível em {url}."


NATIVAS = {"web_search": web_search, "web_fetch": web_fetch}


# ---------- Registro por Conversa ----------


# REVISAR(human): ativa = ativa_global E toggle da Conversa. Sem linha em conversation_tools,
# o toggle herda ativa_global. ativa_global=false desliga a Tool em todas as Conversas.
# Tool de origem 'google' só existe se o dono da Conversa tem Conector Google (ticket 18).
async def estado_da_conversa(session: AsyncSession, cid: uuid.UUID) -> list[tuple[Tool, bool]]:
    """Cada Tool do registro com o estado efetivo na Conversa."""
    tem_conector = exists().where(
        conectores.Connector.user_id == Conversation.user_id,
        conectores.Connector.provedor == conectores.PROVEDOR,
        Conversation.id == cid,
    )
    q = (
        select(Tool, ConversationTool.ativa)
        .outerjoin(
            ConversationTool,
            (ConversationTool.tool_nome == Tool.nome) & (ConversationTool.conversation_id == cid),
        )
        .where(or_(Tool.origem != conectores.PROVEDOR, tem_conector))
        .order_by(Tool.nome)
    )
    return [(t, t.ativa_global and (a if a is not None else True)) for t, a in (await session.execute(q)).all()]


@dataclass
class Auditada(WrapperToolset[Any]):
    """Grava um Evento tool_call por execução: nome, args, duração, tamanho do resultado."""

    uid: uuid.UUID
    cid: uuid.UUID

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[Any], tool: ToolsetTool[Any]
    ) -> Any:
        t0 = time.perf_counter()
        resultado = await super().call_tool(name, tool_args, ctx, tool)
        async with SessionLocal() as s:
            await audit(
                s,
                "tool_call",
                user_id=self.uid,
                conversation_id=self.cid,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                payload={"tool": name, "args": tool_args, "result_chars": len(str(resultado))},
            )
            await s.commit()
        return resultado


async def toolset_da_conversa(
    session: AsyncSession, uid: uuid.UUID, cid: uuid.UUID, t: httpx.AsyncBaseTransport | None
) -> AbstractToolset[Any]:
    """Só as Tools ativas na Conversa, com a descrição do registro, embrulhadas na auditoria."""
    ts = FunctionToolset[Any]()
    for tool, ativa in await estado_da_conversa(session, cid):
        if ativa and tool.nome in NATIVAS:
            ts.add_function(_ligar(tool.nome, t), name=tool.nome, description=tool.descricao)
        elif ativa and tool.nome in conectores.TOOLS:
            ts.add_function(conectores.ligar(tool.nome, uid, t), name=tool.nome, description=tool.descricao)
    return Auditada(ts, uid, cid)


def _ligar(nome: str, t: httpx.AsyncBaseTransport | None):
    """Função que o modelo vê: só o argumento da tool, com o transporte fixo."""
    if nome == "web_search":

        async def buscar(query: str) -> str:
            return await web_search(query, t)

        return buscar

    async def baixar(url: str) -> str:
        return await web_fetch(url, t)

    return baixar


# ---------- API ----------


class ToolOut(BaseModel):
    nome: str
    origem: str
    descricao: str
    schema_: dict[str, Any] = Field(validation_alias="schema", serialization_alias="schema")
    ativa_global: bool


class ToolGlobalIn(BaseModel):
    ativa_global: bool


class ToolConversaOut(BaseModel):
    nome: str
    origem: str
    descricao: str
    ativa: bool


router = APIRouter(tags=["tools"])
Admin = Annotated[User, Depends(current_superuser)]


@router.get("/api/tools", response_model=list[ToolOut])
async def catalogo(session: Sessao, _: Usuario) -> list[ToolOut]:
    """Todas as Tools do registro."""
    tools = (await session.scalars(select(Tool).order_by(Tool.nome))).all()
    return [ToolOut.model_validate(t, from_attributes=True) for t in tools]


@router.put("/api/tools/{nome}", response_model=ToolOut)
async def alternar_global(nome: str, body: ToolGlobalIn, session: Sessao, user: Admin) -> ToolOut:
    """Liga e desliga a Tool em todas as Conversas."""
    tool = await session.get(Tool, nome)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool inexistente")
    tool.ativa_global = body.ativa_global
    await audit(session, "tool_toggled_global", user_id=user.id, payload={"tool": nome, "ativa_global": body.ativa_global})
    await session.commit()
    return ToolOut.model_validate(tool, from_attributes=True)


async def _lista(session: AsyncSession, cid: uuid.UUID) -> list[ToolConversaOut]:
    return [
        ToolConversaOut(nome=t.nome, origem=t.origem, descricao=t.descricao, ativa=a)
        for t, a in await estado_da_conversa(session, cid)
    ]


@router.get("/api/conversations/{cid}/tools", response_model=list[ToolConversaOut])
async def da_conversa(cid: uuid.UUID, session: Sessao, user: Usuario) -> list[ToolConversaOut]:
    await conversa_do_usuario(session, user, cid)
    return await _lista(session, cid)


@router.put("/api/conversations/{cid}/tools", response_model=list[ToolConversaOut])
async def alternar(
    cid: uuid.UUID, body: dict[str, bool], session: Sessao, user: Usuario
) -> list[ToolConversaOut]:
    """Liga e desliga Tools na Conversa. Corpo parcial: {"web_search": false}."""
    await conversa_do_usuario(session, user, cid)
    existentes = set((await session.scalars(select(Tool.nome))).all())
    if desconhecidas := set(body) - existentes:
        raise HTTPException(status_code=422, detail=f"Tool inexistente: {', '.join(sorted(desconhecidas))}")
    for nome, ativa in body.items():
        q = insert(ConversationTool).values(conversation_id=cid, tool_nome=nome, ativa=ativa)
        await session.execute(q.on_conflict_do_update(index_elements=["conversation_id", "tool_nome"], set_={"ativa": ativa}))
    await audit(session, "tool_toggled", user_id=user.id, conversation_id=cid, payload=body)
    await session.commit()
    return await _lista(session, cid)
