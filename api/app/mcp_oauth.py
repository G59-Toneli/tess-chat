"""Servidor MCP por OAuth: descoberta, DCR, PKCE, troca de code e refresh (ticket 52, ADR 0022).

O iniciar também detecta o caminho de uma URL qualquer: oauth, sem_auth ou token (ticket 56)."""

import secrets
import time
import uuid
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_users.jwt import decode_jwt, generate_jwt
from mcp.client.auth import OAuthRegistrationError, PKCEParameters
from mcp.client.auth.utils import (
    build_oauth_authorization_server_metadata_discovery_urls,
    build_protected_resource_metadata_discovery_urls,
    extract_resource_metadata_from_www_auth,
    extract_scope_from_www_auth,
    get_client_metadata_scopes,
    handle_auth_metadata_response,
    handle_protected_resource_response,
    handle_registration_response,
)
from mcp.shared.auth import OAuthClientMetadata, OAuthMetadata, OAuthToken, ProtectedResourceMetadata
from mcp.shared.auth_utils import resource_url_from_server_url
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import set_committed_value

from app.audit import audit
from app.conectores import _cifrar, _decifrar, _fernet
from app.config import settings
from app.conversas import Sessao, Usuario
from app.db import SessionLocal
from app.mcp import McpServer, UrlRecusada, _cliente, _do_usuario, registrar_tools, validar_url
from app.resiliencia import resumo_erro

CALLBACK = "/api/mcp-servers/oauth/callback"
AUD_STATE = "tess:mcp-oauth"
VALIDADE_STATE = 600
# Pendente entre o iniciar e o callback: code_verifier, nome, url, sid e o cliente do DCR (ticket 57).
COOKIE_PENDENTE = "tess_mcp_pendente"
# Token que vence em menos que isso é renovado antes do turno.
FOLGA_S = 60
TIMEOUT = httpx.Timeout(15.0)
GRANTS = ["authorization_code", "refresh_token"]
SEM_DCR = "Esse servidor exige app registrado."
SEM_OAUTH = "Esse servidor não anuncia OAuth."
# Sonda do passo 2: um initialize sem token. Servidor com OAuth responde 401 com WWW-Authenticate.
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "tess-chat", "version": "1"}},
}


def transporte_mcp_oauth() -> httpx.AsyncBaseTransport | None:
    """Transporte HTTP das rotas OAuth. None é a rede real. Os testes trocam via dependency_overrides."""
    return None


Transporte = Annotated[httpx.AsyncBaseTransport | None, Depends(transporte_mcp_oauth)]


class OAuthRecusado(ValueError):
    """Servidor exige auth, mas sem OAuth com DCR. O iniciar responde modo token."""


def _redirect_uri() -> str:
    return f"{settings.public_base_url}{CALLBACK}"


async def _get(http: httpx.AsyncClient, url: str) -> httpx.Response:
    await validar_url(url)  # URL que veio de metadata: sem isso o metadata fura a barreira de SSRF
    return await http.get(url, headers={"Accept": "application/json"})


# descoberta. Passo 2: initialize sem token. 2xx: o servidor não exige auth e a função
# devolve None (modo sem_auth). Outro status segue para os well-known; sem metadata, só 401/403 vira
# modo token, e o resto é erro real (502). Servidor com OAuth
# responde 401 e o WWW-Authenticate aponta o metadata do recurso (RFC 9728). Sem header, os well-known do SDK entram
# como fallback. O metadata do recurso diz qual é o authorization server; o metadata dele (RFC 8414,
# com os fallbacks OIDC do SDK) diz authorize, token e registration. Toda URL passa por validar_url.
async def _descobrir(
    http: httpx.AsyncClient, url: str
) -> tuple[ProtectedResourceMetadata | None, OAuthMetadata, str | None] | None:
    sonda = await http.post(url, json=INITIALIZE, headers={"Accept": "application/json, text/event-stream"})
    if sonda.is_success:
        return None
    nao_autorizado = sonda.status_code in (401, 403)
    www = extract_resource_metadata_from_www_auth(sonda) if nao_autorizado else None
    escopo = extract_scope_from_www_auth(sonda) if nao_autorizado else None
    prm = None
    for u in build_protected_resource_metadata_discovery_urls(www, url):
        prm = await handle_protected_resource_response(await _get(http, u))
        if prm is not None:
            break
    servidor_auth = str(prm.authorization_servers[0]) if prm and prm.authorization_servers else None
    asm = None
    for u in build_oauth_authorization_server_metadata_discovery_urls(servidor_auth, url):
        seguir, asm = await handle_auth_metadata_response(await _get(http, u))
        if asm is not None or not seguir:
            break
    if asm is None:
        if not nao_autorizado:
            sonda.raise_for_status()
        raise OAuthRecusado(SEM_OAUTH)
    return prm, asm, escopo


# DCR (RFC 7591). Só registro dinâmico: sem registration_endpoint (HubSpot, Slack,
# GitHub) o servidor exige app registrado à mão, e não mantemos um por provedor. Cliente público
# (`token_endpoint_auth_method=none`): o segredo do fluxo é o PKCE, não um client_secret. Os três
# endpoints passam por validar_url antes de qualquer request, inclusive o authorize, que o browser abre.
async def _registrar(
    http: httpx.AsyncClient, prm: ProtectedResourceMetadata | None, asm: OAuthMetadata, escopo: str | None
) -> dict[str, Any]:
    if asm.registration_endpoint is None:
        raise OAuthRecusado(SEM_DCR)
    for u in (asm.registration_endpoint, asm.authorization_endpoint, asm.token_endpoint):
        await validar_url(str(u))
    scope = get_client_metadata_scopes(escopo, prm, asm, GRANTS)
    meta = OAuthClientMetadata(
        redirect_uris=[_redirect_uri()],
        grant_types=GRANTS,
        token_endpoint_auth_method="none",
        client_name="tess-chat",
        scope=scope,
    )
    r = await http.post(str(asm.registration_endpoint), json=meta.model_dump(mode="json", exclude_none=True))
    info = await handle_registration_response(r)
    return {
        "client_id": info.client_id,
        "client_secret": info.client_secret,
        "authorization_endpoint": str(asm.authorization_endpoint),
        "token_endpoint": str(asm.token_endpoint),
        "scope": scope,
    }


# troca e refresh vão ao mesmo token_endpoint. `resource` (RFC 8707) vai junto para o
# token sair amarrado à URL do servidor MCP, como a spec MCP exige. client_secret só se o DCR devolveu.
async def _pedir_token(t: httpx.AsyncBaseTransport | None, oauth: dict[str, Any], form: dict[str, str]) -> OAuthToken:
    await validar_url(oauth["token_endpoint"])
    form = {**form, "client_id": oauth["client_id"], "resource": oauth["resource"]}
    if oauth.get("client_secret"):
        form["client_secret"] = oauth["client_secret"]
    async with httpx.AsyncClient(transport=t, timeout=TIMEOUT) as http:
        r = await http.post(oauth["token_endpoint"], data=form, headers={"Accept": "application/json"})
    r.raise_for_status()
    return OAuthToken.model_validate_json(r.content)


def _gravar_token(srv: McpServer, oauth: dict[str, Any], token: OAuthToken) -> None:
    """Guarda o refresh e a validade em `oauth`, e o Bearer em `headers`: _cliente e toolset não mudam."""
    oauth["refresh_token"] = token.refresh_token or oauth.get("refresh_token")  # sem novo, mantém o antigo
    oauth["expires_at"] = int(time.time()) + token.expires_in if token.expires_in else None
    oauth["scope"] = token.scope or oauth.get("scope")
    srv.oauth = _cifrar(oauth)
    srv.headers = _cifrar({"Authorization": f"Bearer {token.access_token}"})


# refresh antes do turno. Token sem validade não é renovado. Vencendo em menos de 60 s,
# POST grant_type=refresh_token. Falha (400 invalid_grant, sem refresh_token, rede) marca `expirado`:
# o servidor sai do turno até o Usuário reconectar (fail-closed). Sessão própria, como conectores._token,
# para gravar mesmo que o turno falhe depois. O objeto do turno recebe o header novo sem ficar sujo.
async def renovar(srv: McpServer, t: httpx.AsyncBaseTransport | None) -> bool:
    """True se o servidor pode entrar no turno."""
    if srv.estado != "ok":
        return False
    if srv.oauth is None:
        return True
    oauth = _decifrar(srv.oauth)
    vence = oauth.get("expires_at")
    if vence is None or vence - time.time() > FOLGA_S:
        return True
    async with SessionLocal() as s:
        atual = await s.get(McpServer, srv.id)
        if atual is None:
            return False
        base = {"servidor": str(srv.id), "nome": srv.nome}
        try:
            if not oauth.get("refresh_token"):
                raise ValueError("sem refresh_token")
            token = await _pedir_token(t, oauth, {"grant_type": "refresh_token", "refresh_token": oauth["refresh_token"]})
        except (httpx.HTTPError, ValueError) as e:  # UrlRecusada e ValidationError são ValueError
            atual.estado = "expirado"
            await audit(s, "mcp_oauth_refresh_failed", user_id=srv.user_id, payload={**base, **resumo_erro(e)})
            await s.commit()
            set_committed_value(srv, "estado", "expirado")
            return False
        _gravar_token(atual, oauth, token)
        await audit(s, "mcp_oauth_refreshed", user_id=srv.user_id, payload=base)
        await s.commit()
        set_committed_value(srv, "headers", atual.headers)
        set_committed_value(srv, "oauth", atual.oauth)
    return True


# ---------- API ----------


class IniciarIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    url: str = Field(pattern=r"^https?://\S+$")
    sid: uuid.UUID | None = None  # reconectar: reaproveita a linha do Usuário


router = APIRouter(prefix="/api/mcp-servers/oauth", tags=["mcp"])


# o app escolhe o caminho, não o usuário. Nenhum modo grava linha: sem_auth e token
# seguem pelo POST /api/mcp-servers; oauth só grava no callback (ticket 57). SSRF 422, rede 502.
@router.post("/iniciar")
async def iniciar(body: IniciarIn, session: Sessao, user: Usuario, t: Transporte) -> JSONResponse:
    """Detecta o caminho da URL. Com OAuth e DCR, registra o cliente e devolve a URL de consentimento."""
    _fernet()
    srv = await _do_usuario(session, user, body.sid) if body.sid else None
    url, nome = (srv.url, srv.nome) if srv else (body.url, body.nome.strip())
    try:
        await validar_url(url)
        async with httpx.AsyncClient(transport=t, timeout=TIMEOUT) as http:
            descoberta = await _descobrir(http, url)
            if descoberta is None:
                return JSONResponse({"modo": "sem_auth"})
            oauth = await _registrar(http, *descoberta)
    except UrlRecusada as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OAuthRecusado:
        return JSONResponse({"modo": "token"})
    except OAuthRegistrationError as e:
        raise HTTPException(status_code=502, detail=f"Não foi possível registrar o app no servidor OAuth. ({e})") from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Não foi possível falar com o servidor MCP. Confira a URL. ({e})") from e
    asm = descoberta[1]
    oauth["resource"] = resource_url_from_server_url(url)
    if srv is None and await session.scalar(
        select(McpServer.id).where(McpServer.user_id == user.id, McpServer.nome == nome)
    ):
        raise HTTPException(status_code=409, detail="Você já tem um servidor MCP com esse nome")
    pkce = PKCEParameters.generate()
    nonce = secrets.token_urlsafe(16)
    state = generate_jwt({"sub": str(user.id), "nonce": nonce, "aud": AUD_STATE}, settings.jwt_secret, VALIDADE_STATE)
    params = {
        "response_type": "code",
        "client_id": oauth["client_id"],
        "redirect_uri": _redirect_uri(),
        "state": state,
        "code_challenge": pkce.code_challenge,
        "code_challenge_method": "S256",
        "resource": oauth["resource"],
    }
    if oauth["scope"]:
        params["scope"] = oauth["scope"]
    autorizar = oauth["authorization_endpoint"]
    await audit(
        session, "mcp_oauth_started", user_id=user.id,
        payload={"servidor": str(srv.id) if srv else None, "nome": nome, "url": url, "authorization_server": str(asm.issuer)},
    )
    await session.commit()
    r = JSONResponse({"modo": "oauth", "url": f"{autorizar}{'&' if '?' in autorizar else '?'}{urlencode(params)}"})
    # o pendente mora no cookie, não no banco. Linha gravada antes do consentimento
    # sobrava como "aguardando autorização" quando o usuário desistia, e o reconectar desligava o
    # servidor antes de ele autorizar. Cifrado com Fernet: o verifier e o cliente do DCR não ficam
    # legíveis para quem lê o cookie. httpOnly, path só do callback, mesma validade do state. O nonce
    # também vai no state: o callback só aceita o cookie do mesmo fluxo que gerou aquele state.
    pendente = {
        "code_verifier": pkce.code_verifier, "nonce": nonce, "nome": nome, "url": url,
        "sid": str(srv.id) if srv else None, "oauth": oauth,
    }
    r.set_cookie(
        COOKIE_PENDENTE, _cifrar(pendente), max_age=VALIDADE_STATE, path=CALLBACK, httponly=True, samesite="lax",
        secure=settings.env == "prod",
    )
    return r


def _voltar(**query: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.public_base_url}/mcp?{urlencode(query)}", status_code=303)


@router.get("/callback", include_in_schema=False)
async def callback(
    request: Request, session: Sessao, t: Transporte,
    code: str | None = None, state: str | None = None, error: str | None = None,
) -> RedirectResponse:
    """Volta do consentimento: troca o code, lista as tools e devolve o browser à tela /mcp."""
    r = await _concluir(session, t, request.cookies.get(COOKIE_PENDENTE), code, state, error)
    r.delete_cookie(COOKIE_PENDENTE, path=CALLBACK)
    return r


# o state (JWT, 10 min) diz o dono e o nonce; o cookie do pendente amarra o code ao
# browser e ao fluxo que abriu o iniciar. Sem cookie, nada vai ao token_endpoint. A linha só nasce (ou
# muda, no reconectar) depois da troca do code. Listagem que falha com o token novo deixa o servidor
# `expirado`, sem tools novas, com o botão Reconectar no card.
async def _concluir(
    session, t: httpx.AsyncBaseTransport | None, cookie: str | None,
    code: str | None, state: str | None, error: str | None,
) -> RedirectResponse:
    if error:
        return _voltar(erro=error)
    try:
        dados = decode_jwt(state or "", settings.jwt_secret, [AUD_STATE])
        uid, nonce = uuid.UUID(dados["sub"]), str(dados["nonce"])
    except Exception:  # noqa: BLE001  state ausente, adulterado ou vencido
        return _voltar(erro="state_invalido")
    if not code:
        return _voltar(erro="sem_code")
    try:
        pendente = _decifrar(cookie or "")
    except Exception:  # noqa: BLE001  cookie ausente, vencido ou adulterado
        return _voltar(erro="pkce_ausente")
    if not secrets.compare_digest(str(pendente.get("nonce")), nonce):
        return _voltar(erro="state_invalido")  # cookie de outro fluxo
    srv = await session.get(McpServer, uuid.UUID(pendente["sid"])) if pendente["sid"] else None
    if pendente["sid"] and (srv is None or srv.user_id != uid):
        return _voltar(erro="state_invalido")
    oauth = pendente["oauth"]
    form = {
        "grant_type": "authorization_code", "code": code, "redirect_uri": _redirect_uri(),
        "code_verifier": pendente["code_verifier"],
    }
    try:
        token = await _pedir_token(t, oauth, form)
    except (httpx.HTTPError, ValueError):
        return _voltar(erro="troca_falhou")
    if srv is None:
        srv = McpServer(id=uuid.uuid4(), user_id=uid, nome=pendente["nome"], url=pendente["url"], headers=_cifrar({}))
        session.add(srv)
    _gravar_token(srv, oauth, token)
    try:
        await session.flush()  # a FK das tools precisa do servidor antes
    except IntegrityError:
        await session.rollback()
        return _voltar(erro="nome_em_uso")  # outro cadastro pegou o nome depois do iniciar
    base = {"servidor": str(srv.id), "nome": srv.nome, "url": srv.url}
    try:
        async with _cliente(srv.url, _decifrar(srv.headers)) as cli:
            listadas = await cli.list_tools()
    except Exception as e:  # noqa: BLE001  qualquer falha do servidor deixa a conexão expirada
        srv.estado = "expirado"
        await audit(session, "mcp_oauth_list_failed", user_id=uid, payload={**base, **resumo_erro(e)})
        await session.commit()
        return _voltar(erro="listagem_falhou")
    from app.tools import Tool  # tools importa mcp

    novo = not await session.scalar(select(func.count()).select_from(Tool).where(Tool.mcp_server_id == srv.id))
    await registrar_tools(session, srv, listadas)
    srv.estado, srv.ativo = "ok", True
    await audit(session, "mcp_oauth_linked", user_id=uid, payload={**base, "tools": len(listadas)})
    if novo:
        await audit(session, "mcp_server_added", user_id=uid, payload={**base, "tools": len(listadas), "tem_auth": True})
    await session.commit()
    return _voltar(conectado="1")
