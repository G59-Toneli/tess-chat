"""Registro de Tools com toggle por Conversa, e as Tools nativas web_search e web_fetch (ADR 0009)."""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Annotated, Any
from urllib.parse import urlsplit

import httpx
import httpx2
import trafilatura
from fastapi import APIRouter, Depends, HTTPException
from mcp.types import CONNECTION_CLOSED, REQUEST_TIMEOUT
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import FunctionToolset, ModelRetry, RunContext, ToolReturn
from pydantic_ai.toolsets import AbstractToolset, CombinedToolset, WrapperToolset
from pydantic_ai.toolsets.abstract import ToolsetTool
from pydantic_core import SchemaValidator, core_schema
from sqlalchemy import Boolean, ForeignKey, Text, and_, exists, or_, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from tavily import AsyncTavilyClient

from app import conectores, mcp, mcp_oauth
from app.audit import audit
from app.config import settings
from app.auth import User, current_superuser
from app.conversas import Conversation, Sessao, Usuario, conversa_do_usuario
from app.db import Base, SessionLocal
from app.rede import ip_interno
from app.resiliencia import TIMEOUTS, resumo_erro

# Teto do texto que volta ao modelo por chamada (~6k tokens, INFERIDO).
LIMITE_CHARS = 20_000
# Tool MCP devolve schema e JSON: cortar no meio tira campos. 40k cobre o maior visto (36k, Stripe api_details).
LIMITE_CHARS_MCP = 40_000
TRECHO_BUSCA = 600
TIMEOUT = httpx.Timeout(30.0)
# Redirects que o web_fetch segue, validando cada salto.
MAX_SALTOS = 5


class Tool(Base):
    __tablename__ = "tools"

    nome: Mapped[str] = mapped_column(Text, primary_key=True)
    origem: Mapped[str] = mapped_column(Text)  # nativa | mcp
    descricao: Mapped[str] = mapped_column(Text)  # o que o modelo recebe
    descricao_usuario: Mapped[str] = mapped_column(Text)  # o que a tela mostra (ticket 28)
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ativa_global: Mapped[bool] = mapped_column(Boolean)
    padrao_ligada: Mapped[bool] = mapped_column(Boolean, default=True)  # estado sem toggle na Conversa
    mcp_server_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mcp_servers.id", ondelete="CASCADE"))


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
    except Exception as e:  # noqa: BLE001  erro vira texto para o modelo, sem gastar o retry da tool
        return f"web_search falhou: {type(e).__name__}"
    blocos = [
        f"[{i}] {x.get('title', '')}\nURL: {x.get('url', '')}\n{(x.get('content') or '')[:TRECHO_BUSCA]}"
        for i, x in enumerate(r.get("results", []), 1)
    ]
    return "\n\n".join(blocos) or "Nenhum resultado."


async def _recusa(url: str) -> str | None:
    """Motivo para não buscar a URL, em texto para o modelo, ou None. Só http(s) para endereço público."""
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        return f"web_fetch recusado: só URL http:// ou https:// ({url})."
    try:
        interno = await ip_interno(partes.hostname, partes.port or (443 if partes.scheme == "https" else 80))
    except OSError:
        return f"web_fetch falhou: não consegui resolver {partes.hostname}."
    if interno:
        return f"web_fetch recusado: {url} aponta para um endereço interno ({interno})."
    return None


# REVISAR(human): Jina Reader primeiro; qualquer falha (status != 200, corpo vazio, erro de rede)
# cai no GET direto da URL + trafilatura. Texto cortado em LIMITE_CHARS para não estourar o contexto.
# SSRF: o GET direto sai do container, então a URL inicial e cada salto de redirect passam por
# `_recusa` (redirect seguido à mão, até MAX_SALTOS). Ressalva: o httpx resolve o DNS de novo (rebinding).
async def web_fetch(url: str, t: httpx.AsyncBaseTransport | None = None) -> str:
    """Baixa a URL e devolve o texto limpo."""
    if motivo := await _recusa(url):
        return motivo
    async with httpx.AsyncClient(transport=t, timeout=TIMEOUT) as http:
        try:
            r = await http.get(f"https://r.jina.ai/{url}")
            if r.status_code == 200 and r.text.strip():
                return cortar(r.text, LIMITE_CHARS)
        except httpx.HTTPError:
            pass
        try:
            for _ in range(MAX_SALTOS):
                r = await http.get(url)
                if not r.is_redirect:
                    break
                url = str(r.url.join(r.headers["location"]))
                if motivo := await _recusa(url):
                    return motivo
            else:
                return f"web_fetch falhou: mais de {MAX_SALTOS} redirecionamentos."
            r.raise_for_status()
        except httpx.HTTPError as e:
            return f"web_fetch falhou: {type(e).__name__}"
    texto = await asyncio.to_thread(trafilatura.extract, r.text)
    return cortar(texto, LIMITE_CHARS) if texto else f"web_fetch: sem texto extraível em {url}."


NATIVAS = {"web_search": web_search, "web_fetch": web_fetch}


def cortar(texto: str, limite: int) -> str:
    """Corta no teto e avisa o modelo do corte, para ele pedir só o trecho necessário (ticket 31)."""
    if len(texto) <= limite:
        return texto
    return f"{texto[:limite]}\n[resultado cortado em {limite} caracteres; peça só o trecho necessário]"


# ---------- Registro por Conversa ----------


# REVISAR(human): ativa = ativa_global E toggle da Conversa. Sem linha em conversation_tools,
# o toggle vale padrao_ligada (true para todas; gmail_send também, desde a 0015: a trava é o clique em Enviar, ADR 0013).
# ativa_global=false desliga a Tool em todas as Conversas.
# Tool de origem 'google' só existe se o dono da Conversa tem Conector Google (ticket 18).
# gmail_send exige também o escopo gmail.send no Conector: conexão antiga não ganha a Tool (ticket 25).
# Conta Google sem caixa Gmail (gmail_disponivel=false) perde as Tools do Gmail; Drive fica (ticket 29).
# Tool de origem 'mcp' só existe para o dono do Servidor MCP, e só com o servidor ativo (ticket 17).
async def estado_da_conversa(session: AsyncSession, cid: uuid.UUID) -> list[tuple[Tool, bool]]:
    """Cada Tool do registro com o estado efetivo na Conversa."""
    tem_conector = exists().where(
        conectores.Connector.user_id == Conversation.user_id,
        conectores.Connector.provedor == conectores.PROVEDOR,
        Conversation.id == cid,
        or_(Tool.nome != "gmail_send", conectores.Connector.escopos.any(conectores.ESCOPO_ENVIO)),
        or_(Tool.nome.not_in(conectores.TOOLS_GMAIL), conectores.Connector.gmail_disponivel),
    )
    servidor_do_dono = exists().where(
        mcp.McpServer.id == Tool.mcp_server_id,
        mcp.McpServer.user_id == Conversation.user_id,
        mcp.McpServer.ativo,
        Conversation.id == cid,
    )
    q = (
        select(Tool, ConversationTool.ativa)
        .outerjoin(
            ConversationTool,
            (ConversationTool.tool_nome == Tool.nome) & (ConversationTool.conversation_id == cid),
        )
        .where(or_(Tool.origem == "nativa", and_(Tool.origem == conectores.PROVEDOR, tem_conector), servidor_do_dono))
        .order_by(Tool.nome)
    )
    return [(t, t.ativa_global and (a if a is not None else t.padrao_ligada)) for t, a in (await session.execute(q)).all()]


# REVISAR(human): o Gemini, com schema aberto (`parameters: object` sem propriedades, caso do Stripe),
# manda objeto aninhado como string JSON. Só string que começa com { ou [ e passa no json.loads vira
# objeto/lista; o resultado é percorrido de novo (string dentro de string). "Olá {mundo}" não muda.
# Risco aceito: string legítima que é JSON válido vira objeto (ticket 33).
def desembrulhar_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {k: desembrulhar_json(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [desembrulhar_json(v) for v in valor]
    if isinstance(valor, str) and valor.lstrip().startswith(("{", "[")):
        try:
            obj = json.loads(valor)
        except ValueError:
            return valor
        return desembrulhar_json(obj) if isinstance(obj, (dict, list)) else valor
    return valor


def _livre(s: Any) -> bool:
    """Objeto sem properties, ou lista desses objetos."""
    if not isinstance(s, dict):
        return False
    if s.get("type") == "object":
        return not s.get("properties")
    return s.get("type") == "array" and _livre(s.get("items"))


# REVISAR(human): o Gemini roda em modo VALIDATED e impõe o schema declarado. Objeto sem properties
# vira objeto vazio: o modelo manda null ou inventa chaves (Stripe, ticket 35). Esse campo passa a ser
# string com JSON; o call_tool da Auditada desembrulha antes de chamar o servidor. Objeto com
# properties só é percorrido. O registro guarda o schema original; só a definição do turno muda.
def schema_para_modelo(schema: dict[str, Any]) -> dict[str, Any]:
    props = schema.get("properties")
    if not isinstance(props, dict):
        return schema
    novas: dict[str, Any] = {}
    for nome, p in props.items():
        if _livre(p):
            sufixo = "JSON serializado do objeto" if p["type"] == "object" else "JSON serializado da lista"
            desc = p.get("description")
            novas[nome] = {"type": "string", "description": f"{desc} — {sufixo}" if desc else sufixo}
        elif isinstance(p, dict) and p.get("type") == "object":
            novas[nome] = schema_para_modelo(p)
        else:
            novas[nome] = p
    return {**schema, "properties": novas}


# O ToolManager valida os args antes do toolset e, na 2ª falha, levanta erro que escapa do ComTeto.
# Ele passa a aceitar tudo; a validação real roda no call_tool da Auditada (ticket 33).
ACEITA_TUDO = SchemaValidator(core_schema.any_schema())


def _args_invalidos(exc: ValidationError) -> ModelRetry:
    campos = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'args'}: {e['msg']}" for e in exc.errors())
    return ModelRetry(f"Argumentos inválidos: {campos}")


@dataclass
class Auditada(WrapperToolset[Any]):
    """Grava um Evento tool_call por execução: nome, args, duração, tamanho do resultado ou o erro."""

    uid: uuid.UUID
    cid: uuid.UUID
    origens: dict[str, str]
    fora_do_ar: list[str] = field(default_factory=list)  # nomes dos Servidores MCP que a sonda tirou do turno
    servidores: dict[str, str] = field(default_factory=dict)  # tool MCP -> nome do Servidor MCP
    # Validador original de cada tool. Objeto compartilhado: o Pydantic AI copia o toolset a cada passo.
    validadores: dict[str, Any] = field(default_factory=dict)

    async def get_tools(self, ctx: RunContext[Any]) -> dict[str, ToolsetTool[Any]]:
        tools = await super().get_tools(ctx)
        self.validadores.update({nome: t.args_validator for nome, t in tools.items()})
        return {nome: replace(t, args_validator=ACEITA_TUDO, tool_def=self._definicao(nome, t)) for nome, t in tools.items()}

    def _definicao(self, nome: str, t: ToolsetTool[Any]) -> Any:
        if self.origens.get(nome) != "mcp":
            return t.tool_def
        return replace(t.tool_def, parameters_json_schema=schema_para_modelo(t.tool_def.parameters_json_schema))

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[Any], tool: ToolsetTool[Any]
    ) -> Any:
        t0 = time.perf_counter()
        if self.origens.get(name) == "mcp":
            tool_args = desembrulhar_json(tool_args)
        base = {"tool": name, "origem": self.origens.get(name), "args": tool_args}
        try:
            validador = self.validadores.get(name)
            if validador is not None:
                try:
                    tool_args = validador.validate_python(tool_args, context=ctx.validation_context)
                except ValidationError as e:
                    raise _args_invalidos(e) from e
            resultado = await super().call_tool(name, tool_args, ctx, tool)
        except Exception as exc:
            await self._auditar(t0, {**base, "erro": resumo_erro(exc)})
            raise
        # Arquivo devolvido (PDF do Drive): conta só o texto; mime e bytes vêm do metadata.
        if isinstance(resultado, ToolReturn):
            extra = {"result_chars": len(str(resultado.return_value)), **(resultado.metadata or {})}
        else:
            extra = {"result_chars": len(str(resultado))}
        await self._auditar(t0, {**base, **extra})
        # Nativa já volta cortada; MCP não tinha teto (ticket 31). Dict corta como JSON, não repr.
        if self.origens.get(name) == "mcp":
            texto = resultado if isinstance(resultado, str) else json.dumps(resultado, ensure_ascii=False, default=str)
            if len(texto) > LIMITE_CHARS_MCP:
                return cortar(texto, LIMITE_CHARS_MCP)
        return resultado

    async def _auditar(self, t0: float, payload: dict[str, Any]) -> None:
        async with SessionLocal() as s:
            await audit(
                s,
                "tool_call",
                user_id=self.uid,
                conversation_id=self.cid,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                payload=payload,
            )
            await s.commit()


async def toolset_da_conversa(
    session: AsyncSession, uid: uuid.UUID, cid: uuid.UUID, t: httpx.AsyncBaseTransport | None
) -> AbstractToolset[Any]:
    """Só as Tools ativas na Conversa, com a descrição do registro, embrulhadas na auditoria."""
    ts = FunctionToolset[Any]()
    por_servidor: dict[uuid.UUID, set[str]] = {}
    ativas = [tool for tool, ativa in await estado_da_conversa(session, cid) if ativa]
    for tool in ativas:
        if tool.nome in NATIVAS:
            ts.add_function(_ligar(tool.nome, t), name=tool.nome, description=tool.descricao)
        elif tool.nome in conectores.TOOLS:
            ts.add_function(conectores.ligar(tool.nome, uid, t, cid), name=tool.nome, description=tool.descricao)
        elif tool.mcp_server_id is not None:
            por_servidor.setdefault(tool.mcp_server_id, set()).add(tool.nome)
    candidatos = (await session.scalars(select(mcp.McpServer).where(mcp.McpServer.id.in_(por_servidor)))).all()
    # OAuth vencendo renova antes da sonda; aguardando ou expirado sai do turno (ticket 52).
    usaveis = await asyncio.gather(*(mcp_oauth.renovar(s, t) for s in candidatos))
    servidores = [s for s, ok in zip(candidatos, usaveis, strict=True) if ok]
    fora = [s.nome for s, ok in zip(candidatos, usaveis, strict=True) if not ok]
    # Servidor fora do ar sai do turno em vez de derrubá-lo (ticket 23). Sondas em paralelo.
    erros = await asyncio.gather(*(mcp.alcancavel(s) for s in servidores))
    vivos = []
    for srv, erro in zip(servidores, erros, strict=True):
        if erro is None:
            vivos.append(srv)
            continue
        fora.append(srv.nome)
        await audit(
            session,
            "mcp_server_unreachable",
            user_id=uid,
            conversation_id=cid,
            payload={"servidor": str(srv.id), "nome": srv.nome, **resumo_erro(erro)},
        )
    todos = CombinedToolset([ts, *(mcp.toolset(s, por_servidor[s.id]) for s in vivos)])
    nomes = {s.id: s.nome for s in vivos}
    servidores = {t: nomes[sid] for sid, grupo in por_servidor.items() if sid in nomes for t in grupo}
    return Auditada(todos, uid, cid, {tool.nome: tool.origem for tool in ativas}, fora, servidores)


# REVISAR(human): falha do servidor MCP, não da tool. O MCPToolset embrulha o MCPError do SDK
# num ModelRetry; o código dele diz se foi timeout (REQUEST_TIMEOUT) ou conexão (CONNECTION_CLOSED).
# Erro que a tool devolve (ToolError, MCPError de outro código) não corta: segue ao modelo.
def _falha_mcp(exc: BaseException) -> str | None:
    e: BaseException | None = exc
    while e is not None:
        codigo = getattr(getattr(e, "error", None), "code", None)
        if codigo == REQUEST_TIMEOUT or isinstance(e, TIMEOUTS):
            return "mcp_timeout"
        if codigo == CONNECTION_CLOSED or isinstance(e, (httpx.TransportError, httpx2.TransportError)):
            return "mcp_fora_do_ar"
        e = e.__cause__ or e.__context__
    return None


@dataclass
class Corte:
    chamadas: int = 0
    interrupcao: dict[str, Any] | None = None


@dataclass
class ComTeto(WrapperToolset[Any]):
    """Corta o turno por fora do modelo: teto de chamadas ou tool MCP que caiu (ticket 30).

    Cancela o run em vez de levantar erro. O Pydantic AI fecha a tool pendente como interrompida
    e entrega mensagens e uso ao `on_cancel` do chat, que persiste e cobra o turno.
    """

    wrapped: Auditada
    limite: int
    # O Pydantic AI copia o toolset a cada passo (dataclasses.replace): o estado mora num objeto compartilhado.
    corte: Corte = field(default_factory=Corte)

    async def _cortar(self, ctx: RunContext[Any], interrupcao: dict[str, Any]) -> None:
        self.corte.interrupcao = interrupcao
        ctx.cancel()
        await asyncio.sleep(0)  # o cancelamento chega aqui; a tool não roda
        raise RuntimeError("turno cancelado")  # defesa: não deve ser alcançado

    async def __aexit__(self, *args: Any) -> bool | None:
        try:
            return await super().__aexit__(*args)
        except Exception:
            # Servidor MCP que caiu falha de novo ao fechar a sessão. Esse erro trocaria o
            # cancelamento por erro genérico no stream; o corte já está registrado.
            if self.corte.interrupcao is None or self.corte.interrupcao["motivo"] == "tool_limit_reached":
                raise
            return None

    # REVISAR(human): o que corta o turno. A (limite+1)ª chamada não roda; o teto conta chamadas,
    # não requests, porque é o que o Usuário vê como cards. Tool MCP cujo servidor caiu ou estourou
    # o timeout também corta: repetir no mesmo turno só gastaria mais requests.
    # Erro da tool (ModelRetry, ticket 31) volta ao modelo uma vez. A falha seguida da mesma tool
    # corta com "A tool X falhou": ctx.retry chegou em max_retries (Agent retries=1). O framework
    # zera ctx.retry quando a tool acerta, então só conta falha seguida. Com retries=0 o corte
    # seria imediato, sem nova tentativa.
    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[Any], tool: ToolsetTool[Any]
    ) -> Any:
        self.corte.chamadas += 1
        if self.corte.chamadas > self.limite:
            await self._cortar(ctx, {"motivo": "tool_limit_reached", "limite": self.limite})
        try:
            return await super().call_tool(name, tool_args, ctx, tool)
        except Exception as exc:
            motivo = _falha_mcp(exc) if self.wrapped.origens.get(name) == "mcp" else None
            servidor = self.wrapped.servidores.get(name)
            if motivo is not None:
                await self._cortar(ctx, {"motivo": motivo, "servidor": servidor, "tool": name, **resumo_erro(exc)})
            if isinstance(exc, ModelRetry) and ctx.retry >= ctx.max_retries:
                await self._cortar(ctx, {"motivo": "tool_falhou", "servidor": servidor, "tool": name, **resumo_erro(exc)})
            raise


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
    descricao_usuario: str
    schema_: dict[str, Any] = Field(validation_alias="schema", serialization_alias="schema")
    ativa_global: bool


class ToolGlobalIn(BaseModel):
    ativa_global: bool


class ToolConversaOut(BaseModel):
    nome: str
    origem: str
    descricao: str
    descricao_usuario: str
    ativa: bool
    servidor: str | None = None  # nome do Servidor MCP, só em origem mcp


router = APIRouter(tags=["tools"])
Admin = Annotated[User, Depends(current_superuser)]


@router.get("/api/tools", response_model=list[ToolOut])
async def catalogo(session: Sessao, user: Usuario) -> list[ToolOut]:
    """Todas as Tools do registro, menos as MCP de outros Usuários."""
    meus = select(mcp.McpServer.id).where(mcp.McpServer.user_id == user.id)
    q = select(Tool).where(or_(Tool.mcp_server_id.is_(None), Tool.mcp_server_id.in_(meus))).order_by(Tool.nome)
    tools = (await session.scalars(q)).all()
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
    estado = await estado_da_conversa(session, cid)
    ids = {t.mcp_server_id for t, _ in estado if t.mcp_server_id}
    q = select(mcp.McpServer.id, mcp.McpServer.nome).where(mcp.McpServer.id.in_(ids))
    servidores = dict((await session.execute(q)).tuples().all()) if ids else {}
    return [
        ToolConversaOut(
            nome=t.nome,
            origem=t.origem,
            descricao=t.descricao,
            descricao_usuario=t.descricao_usuario,
            ativa=a,
            servidor=servidores.get(t.mcp_server_id),
        )
        for t, a in estado
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
