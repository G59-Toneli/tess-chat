"""Servidor MCP por Usuário: cadastro, listagem das tools e toolset do turno (ticket 17, ADR 0009)."""

import asyncio
import ipaddress
import re
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset
from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.conectores import _cifrar, _decifrar
from app.config import settings
from app.conversas import Sessao, Usuario
from app.db import Base
from app.resiliencia import resumo_erro

# Timeout do handshake e de cada chamada. Servidor lento não segura o cadastro nem o turno.
TIMEOUT_S = 15.0
# Sonda do turno: servidor que não responde nisso fica fora do turno (ticket 23).
SONDA_S = 3.0
# Limite de nome de function do Gemini.
LIMITE_NOME = 64
LIMITE_DESCRICAO_USUARIO = 140  # ticket 28: cabe em duas linhas no seletor de tools
# Hosts do servidor demo liberados em http quando ENV=dev: dentro e fora do compose.
HOSTS_DEMO = {"mcp-demo", "127.0.0.1"}


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    headers: Mapped[str] = mapped_column(Text)  # JSON {nome: valor} cifrado com Fernet
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Nulo: cadastro por header. Com OAuth, `headers` guarda o Bearer do access token atual (ticket 52).
    oauth: Mapped[str | None] = mapped_column(Text)  # JSON cifrado com Fernet
    estado: Mapped[str] = mapped_column(Text, default="ok")  # ok | aguardando_oauth | expirado
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# REVISAR(human): `tools.nome` é PK global, e dois Usuários podem cadastrar o mesmo servidor.
# O nome no registro vira <slug do servidor>_<4 hex do id>_<tool>: legível para o modelo e único
# entre Usuários. É o mesmo nome que MCPToolset.prefixed() expõe ao modelo no turno.
def prefixo(srv: McpServer) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", srv.nome.lower()).strip("_")[:20] or "mcp"
    if not slug[0].isalpha():
        slug = f"m{slug}"
    return f"{slug}_{srv.id.hex[:4]}"


def _cliente(url: str, headers: dict[str, str], timeout: float = TIMEOUT_S) -> MCPToolset:
    return MCPToolset(url, headers=headers, init_timeout=timeout, read_timeout=timeout)


class UrlRecusada(ValueError):
    """URL de Servidor MCP fora da política. A mensagem vai para o usuário."""


# REVISAR(human): barreira de SSRF no cadastro. Só https, e todo IP que o host resolve precisa ser
# público (`is_global` recusa privado, loopback, link-local 169.254 da metadata, reservado).
# Checa TODOS os IPs: um host com um IP público e um interno passaria se olhasse só o primeiro.
# Exceção: em dev, o demo em http. Ressalva: o turno resolve o DNS de novo (rebinding não coberto).
async def validar_url(url: str) -> None:
    partes = urlsplit(url)
    host = (partes.hostname or "").lower()
    if settings.env == "dev" and host in HOSTS_DEMO:
        return
    if partes.scheme != "https":
        raise UrlRecusada("A URL do servidor MCP precisa usar https://.")
    try:
        ips = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, partes.port or 443)
        except OSError as e:
            raise UrlRecusada(f"Não consegui resolver o host da URL ({host}).") from e
        ips = [ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos]
    for ip in ips:
        real = ip.ipv4_mapped if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped else ip
        if not real.is_global:
            raise UrlRecusada(f"A URL aponta para um endereço interno ({real}). Use um servidor MCP público.")


async def alcancavel(srv: McpServer) -> BaseException | None:
    """Sonda curta: conecta e lista. Devolve o erro, ou None se o servidor respondeu."""
    try:
        async with asyncio.timeout(SONDA_S + 1):
            async with _cliente(srv.url, _decifrar(srv.headers), SONDA_S) as cli:
                await cli.list_tools()
    except Exception as e:  # noqa: BLE001  qualquer falha tira o servidor do turno
        return e
    return None


def toolset(srv: McpServer, ativas: set[str]) -> AbstractToolset[Any]:
    """Toolset do turno: só as tools ativas na Conversa, com o nome do registro."""
    cli = _cliente(srv.url, _decifrar(srv.headers))
    return cli.prefixed(prefixo(srv)).filtered(lambda _ctx, td: td.name in ativas)


def _cabecalhos(autorizacao: str | None) -> dict[str, str]:
    """Valor do header Authorization. Token solto (sem espaço) vira Bearer."""
    if not autorizacao or not autorizacao.strip():
        return {}
    v = autorizacao.strip()
    return {"Authorization": v if " " in v else f"Bearer {v}"}


# ---------- API ----------


class McpServerIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    url: str = Field(pattern=r"^https?://\S+$")  # ADR 0009: só Streamable HTTP
    autorizacao: str | None = None


class McpAtivoIn(BaseModel):
    ativo: bool


class McpToolOut(BaseModel):
    nome: str
    descricao: str
    descricao_usuario: str


class McpServerOut(BaseModel):
    id: uuid.UUID
    nome: str
    url: str
    ativo: bool
    tem_auth: bool
    estado: str
    oauth: bool
    created_at: datetime
    tools: list[McpToolOut]


router = APIRouter(prefix="/api/mcp-servers", tags=["mcp"])


async def _saida(session: Sessao, srv: McpServer) -> McpServerOut:
    from app.tools import Tool  # tools importa este módulo

    tools = (await session.scalars(select(Tool).where(Tool.mcp_server_id == srv.id).order_by(Tool.nome))).all()
    return McpServerOut(
        id=srv.id,
        nome=srv.nome,
        url=srv.url,
        ativo=srv.ativo,
        tem_auth=bool(_decifrar(srv.headers)),
        estado=srv.estado,
        oauth=srv.oauth is not None,
        created_at=srv.created_at,
        tools=[McpToolOut(nome=t.nome, descricao=t.descricao, descricao_usuario=t.descricao_usuario) for t in tools],
    )


async def _do_usuario(session: Sessao, user: Usuario, sid: uuid.UUID) -> McpServer:
    srv = await session.get(McpServer, sid)
    if srv is None or srv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Servidor MCP inexistente")
    return srv


@router.get("", response_model=list[McpServerOut])
async def listar(session: Sessao, user: Usuario) -> list[McpServerOut]:
    """Servidores MCP do Usuário com as tools de cada um. O header nunca volta."""
    q = select(McpServer).where(McpServer.user_id == user.id).order_by(McpServer.created_at)
    return [await _saida(session, s) for s in (await session.scalars(q)).all()]


async def registrar_tools(session: Sessao, srv: McpServer, listadas: list[Any]) -> None:
    """Grava no registro as tools listadas que ainda não estão lá. Reconectar não duplica nem perde toggles."""
    from app.tools import Tool  # tools importa este módulo

    ja = set((await session.scalars(select(Tool.nome).where(Tool.mcp_server_id == srv.id))).all())
    p = prefixo(srv)
    for t in listadas:
        nome = f"{p}_{t.name}"
        if len(nome) <= LIMITE_NOME and nome not in ja:
            descricao = t.description or t.name
            session.add(
                Tool(
                    nome=nome,
                    origem="mcp",
                    descricao=descricao,
                    descricao_usuario=descricao[:LIMITE_DESCRICAO_USUARIO],  # sem texto próprio: a do servidor, curta
                    schema=t.input_schema,
                    ativa_global=True,
                    mcp_server_id=srv.id,
                )
            )


# REVISAR(human): conecta e lista as tools ANTES de gravar qualquer linha. Falha de rede, 401 ou
# protocolo vira 502 com texto legível e nada fica no banco. Tool com nome acima do limite do
# Gemini fica de fora do registro (o modelo recusaria a declaração).
@router.post("", response_model=McpServerOut, status_code=201)
async def cadastrar(body: McpServerIn, session: Sessao, user: Usuario) -> McpServerOut:
    """Conecta no servidor, lista as tools e grava servidor e tools no registro com origem mcp."""
    try:
        await validar_url(body.url)
    except UrlRecusada as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    headers = _cabecalhos(body.autorizacao)
    try:
        async with _cliente(body.url, headers) as cli:
            listadas = await cli.list_tools()
    except Exception as e:  # noqa: BLE001  qualquer falha do servidor vira erro legível
        motivo = str(e) or type(e).__name__
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível conectar ao servidor MCP. Confira a URL e o header de autenticação. ({motivo})",
        ) from e
    srv = McpServer(id=uuid.uuid4(), user_id=user.id, nome=body.nome.strip(), url=body.url, headers=_cifrar(headers))
    session.add(srv)
    try:
        await session.flush()  # a FK das tools precisa do servidor antes
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="Você já tem um servidor MCP com esse nome") from e
    await registrar_tools(session, srv, listadas)
    await audit(
        session,
        "mcp_server_added",
        user_id=user.id,
        payload={"servidor": str(srv.id), "nome": srv.nome, "url": srv.url, "tools": len(listadas), "tem_auth": bool(headers)},
    )
    await session.commit()
    await session.refresh(srv)
    return await _saida(session, srv)


@router.put("/{sid}", response_model=McpServerOut)
async def alternar(sid: uuid.UUID, body: McpAtivoIn, session: Sessao, user: Usuario) -> McpServerOut:
    """Liga e desliga o servidor. Desligado, as tools dele somem de todas as Conversas."""
    srv = await _do_usuario(session, user, sid)
    srv.ativo = body.ativo
    await audit(session, "mcp_server_toggled", user_id=user.id, payload={"servidor": str(sid), "ativo": body.ativo})
    await session.commit()
    await session.refresh(srv)
    return await _saida(session, srv)


@router.delete("/{sid}", status_code=204)
async def remover(sid: uuid.UUID, session: Sessao, user: Usuario) -> Response:
    """Apaga o servidor. O cascade leva as tools e os toggles por Conversa."""
    srv = await _do_usuario(session, user, sid)
    nome = srv.nome
    await session.delete(srv)
    await audit(session, "mcp_server_removed", user_id=user.id, payload={"servidor": str(sid), "nome": nome})
    await session.commit()
    return Response(status_code=204)
