"""Conector Google (ticket 18). Google fica atrás de MockTransport: OAuth, Gmail e Drive gravados."""

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic_ai.messages import BinaryContent, ModelMessage, ModelRequest, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from sqlalchemy import text

from app.anexos import MEDIA_PDF
from app.chat import MODELO
from app.conectores import CALLBACK, COOKIE_PKCE, transporte_google
from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.tools import transporte
from tests.test_auth import eventos
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario

GOOGLE_TOOLS = {"gmail_search", "gmail_read", "drive_search_read"}
LEITURA = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly"
COM_ENVIO = f"{LEITURA} https://www.googleapis.com/auth/gmail.send"
ARQUIVOS = [
    {"id": "d1", "name": "Plano Q4", "mimeType": "application/vnd.google-apps.document"},
    {
        "id": "d2", "name": "foto.png", "mimeType": "image/png",
        "createdTime": "2026-09-20T12:00:00.000Z", "modifiedTime": "2026-09-23T13:05:00.000Z",
    },
]
PDF = b"%PDF-1.4 guia autorizada 123"
GUIA = {"id": "p1", "name": "guia.pdf", "mimeType": "application/pdf", "size": str(len(PDF))}
# Resposta real do Gmail para conta Google sem caixa Gmail (criada com e-mail de outro provedor).
SEM_GMAIL = {"error": {"code": 400, "message": "Mail service not enabled", "status": "FAILED_PRECONDITION"}}


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


class Google(httpx.MockTransport):
    """Token, revoke, Gmail e Drive do Google, com resposta gravada. Guarda os requests vistos."""

    def __init__(
        self,
        refresh_ok: bool = True,
        escopos: str = COM_ENVIO,
        envio_status: int = 200,
        envio_erro: str = "Request had insufficient authentication scopes.",
        gmail_ativo: bool = True,
        arquivos: list[dict] | None = None,
    ):
        self.arquivos = arquivos if arquivos is not None else ARQUIVOS
        self.vistas: list[httpx.Request] = []
        self.refresh_ok = refresh_ok
        self.escopos = escopos
        self.envio_status = envio_status
        self.envio_erro = envio_erro
        self.gmail_ativo = gmail_ativo
        self.emitidos = 0
        super().__init__(self._responder)

    def _token(self, req: httpx.Request) -> httpx.Response:
        form = parse_qs(req.content.decode())
        if form["grant_type"] == ["refresh_token"] and not self.refresh_ok:
            return httpx.Response(400, json={"error": "invalid_grant"})
        self.emitidos += 1
        corpo = {
            "access_token": f"acesso-{self.emitidos}",
            "expires_in": 3599,
            "scope": self.escopos,
            "token_type": "Bearer",
        }
        if form["grant_type"] == ["authorization_code"]:
            corpo["refresh_token"] = "refresh-1"
        return httpx.Response(200, json=corpo)

    def _responder(self, req: httpx.Request) -> httpx.Response:
        self.vistas.append(req)
        u = req.url
        if u.host == "oauth2.googleapis.com" and u.path == "/token":
            return self._token(req)
        if u.host == "oauth2.googleapis.com" and u.path == "/revoke":
            return httpx.Response(200)
        if u.path == "/gmail/v1/users/me/profile":
            if not self.gmail_ativo:
                return httpx.Response(400, json=SEM_GMAIL)
            return httpx.Response(200, json={"emailAddress": "usuario@gmail.com", "messagesTotal": 10})
        if u.path == "/drive/v3/about":
            return httpx.Response(200, json={"user": {"emailAddress": "usuario@outlook.com"}})
        if u.path == "/gmail/v1/users/me/messages":
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        if u.path == "/gmail/v1/users/me/messages/m1":
            headers = [
                {"name": "From", "value": "Ana <ana@exemplo.com>"},
                {"name": "Subject", "value": "Fatura de setembro"},
                {"name": "Date", "value": "Mon, 22 Sep 2026 10:00:00 -0300"},
            ]
            corpo = {"mimeType": "text/plain", "body": {"data": b64("Segue a fatura no valor de R$ 123,45.")}}
            payload = {"headers": headers, "mimeType": "multipart/alternative", "parts": [corpo]}
            return httpx.Response(200, json={"id": "m1", "threadId": "t1", "snippet": "Segue a fatura", "payload": payload})
        if u.path == "/gmail/v1/users/me/threads/t1":
            antigo = [{"name": "Message-ID", "value": "<primeiro@exemplo.com>"}]
            ultimo = [
                {"name": "Message-ID", "value": "<fatura-set@exemplo.com>"},
                {"name": "References", "value": "<primeiro@exemplo.com>"},
            ]
            msgs = [{"id": "m0", "payload": {"headers": antigo}}, {"id": "m1", "payload": {"headers": ultimo}}]
            return httpx.Response(200, json={"id": "t1", "messages": msgs})
        if u.path == "/gmail/v1/users/me/messages/send":
            if self.envio_status != 200:
                erro = {"error": {"code": self.envio_status, "message": self.envio_erro}}
                return httpx.Response(self.envio_status, json=erro)
            return httpx.Response(200, json={"id": "enviado-1", "threadId": "t1", "labelIds": ["SENT"]})
        if u.path == "/drive/v3/files":
            return httpx.Response(200, json={"files": self.arquivos})
        if u.path == "/drive/v3/files/p1" and u.params.get("alt") == "media":
            return httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})
        if u.path == "/drive/v3/files/d1/export":
            return httpx.Response(200, text="Plano Q4: lançar o conector em outubro.")
        return httpx.Response(404, json={"error": "rota não gravada"})

    def bearer(self, host_path: str) -> list[str]:
        return [r.headers.get("authorization", "") for r in self.vistas if host_path in str(r.url)]


@pytest.fixture
def google():
    """O mesmo MockTransport nas rotas do Conector e nas Tools do chat."""
    g = Google()
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    yield g
    app.dependency_overrides.pop(transporte_google, None)
    app.dependency_overrides.pop(transporte, None)


async def autorizar(client, h) -> dict[str, list[str]]:
    r = await client.get("/api/connectors/google/authorize", headers=h)
    assert r.status_code == 200, r.text
    return parse_qs(urlparse(r.json()["url"]).query)


async def conectar(client, h) -> None:
    q = await autorizar(client, h)
    r = await client.get(CALLBACK, params={"code": "code-falso", "state": q["state"][0]})
    assert r.status_code in (302, 303, 307), r.text
    assert r.headers["location"].endswith("/conectores?conectado=1")


async def expirar(uid) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text("UPDATE connectors SET expira_em = :t WHERE user_id = :u"),
            {"t": datetime.now(UTC) - timedelta(minutes=5), "u": uid},
        )
        await s.commit()


def retornos(msgs: list[ModelMessage]) -> list[ToolReturnPart]:
    return [p for m in msgs if isinstance(m, ModelRequest) for p in m.parts if isinstance(p, ToolReturnPart)]


def modelo_que_chama(tool: str, args: dict, vistos: list[AgentInfo]):
    """Chama `tool` no 1º request se ela existir. No 2º devolve o retorno da tool como texto."""

    async def stream(msgs: list[ModelMessage], info: AgentInfo):
        vistos.append(info)
        feitos = retornos(msgs[-1:])
        if not feitos and tool in [t.name for t in info.function_tools]:
            yield {0: DeltaToolCall(name=tool, json_args=json.dumps(args), tool_call_id="c1")}
            return
        yield f"Resposta: {feitos[-1].content}" if feitos else "Sem tool."

    return FunctionModel(stream_function=stream, model_name=MODELO)


async def ultima_resposta(client, h, cid) -> str:
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    return msgs[-1]["parts"][-1]["text"]


# ---------- OAuth ----------


async def test_authorize_monta_url_do_google(client):
    _, h = await usuario(client)
    r = await client.get("/api/connectors/google/authorize", headers=h)

    assert r.status_code == 200, r.text
    url = urlparse(r.json()["url"])
    q = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert q["client_id"] == [settings.google_client_id]
    assert q["redirect_uri"] == [f"{settings.public_base_url}/api/connectors/google/callback"]
    assert set(q["scope"][0].split()) == set(COM_ENVIO.split())
    assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"]
    assert q["state"][0]
    assert (await client.get("/api/connectors/google/authorize")).status_code == 401


async def test_authorize_liga_pkce_e_guarda_o_verifier_em_cookie(client):
    _, h = await usuario(client)
    r = await client.get("/api/connectors/google/authorize", headers=h)

    q = parse_qs(urlparse(r.json()["url"]).query)
    assert q["code_challenge_method"] == ["S256"] and q["code_challenge"][0]
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_PKCE}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and f"Path={CALLBACK}" in cookie


async def test_callback_manda_o_verifier_que_bate_com_o_challenge(client, google):
    _, h = await usuario(client)
    q = await autorizar(client, h)

    r = await client.get(CALLBACK, params={"code": "code-falso", "state": q["state"][0]})

    assert r.headers["location"].endswith("/conectores?conectado=1")
    [troca] = [r for r in google.vistas if r.url.path == "/token"]
    verifier = parse_qs(troca.content.decode())["code_verifier"][0]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert challenge == q["code_challenge"][0]
    assert COOKIE_PKCE not in client.cookies


async def test_callback_sem_cookie_pkce_nao_chama_o_google(client, google):
    _, h = await usuario(client)
    q = await autorizar(client, h)
    client.cookies.clear()

    r = await client.get(CALLBACK, params={"code": "code-falso", "state": q["state"][0]})

    assert "/conectores?erro=pkce_ausente" in r.headers["location"]
    assert google.vistas == []
    [c] = (await client.get("/api/connectors", headers=h)).json()
    assert c["conectado"] is False


async def test_callback_troca_code_e_grava_tokens_cifrados(client, google):
    uid, h = await usuario(client)

    await conectar(client, h)

    [troca] = [r for r in google.vistas if r.url.path == "/token"]
    form = parse_qs(troca.content.decode())
    assert form["code"] == ["code-falso"]
    assert form["redirect_uri"] == [f"{settings.public_base_url}{CALLBACK}"]
    [c] = (await client.get("/api/connectors", headers=h)).json()
    assert c["provedor"] == "google" and c["conectado"] is True
    assert "https://www.googleapis.com/auth/gmail.readonly" in c["escopos"]
    async with SessionLocal() as s:
        guardado = (await s.execute(text("SELECT tokens FROM connectors WHERE user_id = :u"), {"u": uid})).scalar_one()
    assert "acesso-1" not in guardado and "refresh-1" not in guardado
    [ev] = await eventos("connector_linked", user_id=uid)
    assert ev.payload["provedor"] == "google"
    assert "acesso-1" not in json.dumps(ev.payload)


async def test_callback_grava_a_conta_vinculada(client, google):
    uid, h = await usuario(client)

    await conectar(client, h)

    [c] = (await client.get("/api/connectors", headers=h)).json()
    assert c["conta_email"] == "usuario@gmail.com"
    assert c["gmail_disponivel"] is True
    [ev] = await eventos("connector_linked", user_id=uid)
    assert ev.payload["conta_email"] == "usuario@gmail.com"


async def test_conta_sem_gmail_marca_indisponivel_e_tira_tools_do_gmail(client):
    g = Google(gmail_ativo=False)
    app.dependency_overrides[transporte_google] = lambda: g
    try:
        uid, h = await usuario(client)
        cid = (await criar(client, h))["id"]
        q = await autorizar(client, h)
        r = await client.get(CALLBACK, params={"code": "code-falso", "state": q["state"][0]})
        [c] = (await client.get("/api/connectors", headers=h)).json()
        tools = {t["nome"] for t in (await client.get(f"/api/conversations/{cid}/tools", headers=h)).json()}
    finally:
        app.dependency_overrides.pop(transporte_google, None)

    assert "sem_gmail=1" in r.headers["location"]
    assert c["conectado"] is True and c["gmail_disponivel"] is False
    assert c["conta_email"] == "usuario@outlook.com"  # veio do Drive
    assert "drive_search_read" in tools
    assert not {"gmail_search", "gmail_read", "gmail_send"} & tools
    [ev] = await eventos("connector_linked", user_id=uid)
    assert ev.payload["gmail_disponivel"] is False


async def test_conexao_antiga_sem_conta_nao_quebra(client, google):
    uid, h = await usuario(client)
    await conectar(client, h)
    async with SessionLocal() as s:
        await s.execute(text("UPDATE connectors SET conta_email = NULL WHERE user_id = :u"), {"u": uid})
        await s.commit()

    [c] = (await client.get("/api/connectors", headers=h)).json()

    assert c["conectado"] is True and c["conta_email"] is None and c["gmail_disponivel"] is True


async def test_callback_com_state_invalido_nao_conecta(client, google):
    _, h = await usuario(client)

    r = await client.get(CALLBACK, params={"code": "code-falso", "state": "lixo"})

    assert r.status_code in (302, 303, 307)
    assert "/conectores?erro=" in r.headers["location"]
    assert google.vistas == []
    [c] = (await client.get("/api/connectors", headers=h)).json()
    assert c["conectado"] is False


async def test_callback_com_recusa_do_usuario_volta_com_erro(client, google):
    _, h = await usuario(client)
    q = await autorizar(client, h)

    r = await client.get(CALLBACK, params={"error": "access_denied", "state": q["state"][0]})

    assert "/conectores?erro=access_denied" in r.headers["location"]
    assert google.vistas == []


async def test_revogar_desconecta_e_audita(client, google):
    uid, h = await usuario(client)
    await conectar(client, h)

    r = await client.delete("/api/connectors/google", headers=h)

    assert r.status_code == 204
    [c] = (await client.get("/api/connectors", headers=h)).json()
    assert c["conectado"] is False
    assert any(r.url.path == "/revoke" for r in google.vistas)
    [ev] = await eventos("connector_revoked", user_id=uid)
    assert ev.payload["provedor"] == "google"


# ---------- Registro de Tools ----------


async def test_tools_do_google_so_aparecem_com_conector(client, google):
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    nomes = lambda r: {t["nome"] for t in r.json()}  # noqa: E731

    antes = await client.get(f"/api/conversations/{cid}/tools", headers=h)
    await conectar(client, h)
    depois = await client.get(f"/api/conversations/{cid}/tools", headers=h)
    await client.delete("/api/connectors/google", headers=h)
    revogado = await client.get(f"/api/conversations/{cid}/tools", headers=h)

    assert not GOOGLE_TOOLS & nomes(antes)
    assert GOOGLE_TOOLS <= nomes(depois)
    assert {t["origem"] for t in depois.json() if t["nome"] in GOOGLE_TOOLS} == {"google"}
    assert not GOOGLE_TOOLS & nomes(revogado)


async def test_sem_conector_modelo_nao_ve_tools_do_google(client, google, usar_modelo):
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_que_chama("gmail_search", {"query": "fatura"}, vistos))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("meu último e-mail sobre fatura"), headers=h)

    assert r.status_code == 200, r.text
    assert not GOOGLE_TOOLS & {t.name for t in vistos[0].function_tools}
    assert google.vistas == []


# ---------- Tools no chat ----------


async def test_gmail_search_devolve_email_do_usuario(client, google, usar_modelo):
    usar_modelo(modelo_que_chama("gmail_search", {"query": "fatura"}, []))
    uid, h = await usuario(client)
    await conectar(client, h)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("meu último e-mail sobre fatura"), headers=h)

    assert r.status_code == 200, r.text
    resposta = await ultima_resposta(client, h, cid)
    assert "Fatura de setembro" in resposta and "ana@exemplo.com" in resposta and "m1" in resposta
    busca = next(r for r in google.vistas if r.url.path == "/gmail/v1/users/me/messages")
    assert busca.url.params["q"] == "fatura"
    assert set(google.bearer("/users/me/messages")) == {"Bearer acesso-1"}
    [ev] = await eventos("tool_call", user_id=uid)
    assert ev.payload["tool"] == "gmail_search" and ev.payload["args"] == {"query": "fatura"}


async def test_gmail_read_devolve_corpo_em_texto(client, google, usar_modelo):
    usar_modelo(modelo_que_chama("gmail_read", {"message_id": "m1"}, []))
    _, h = await usuario(client)
    await conectar(client, h)
    cid = (await criar(client, h))["id"]

    await client.post(f"/api/chat/{cid}", json=corpo("lê esse e-mail"), headers=h)

    resposta = await ultima_resposta(client, h, cid)
    assert "R$ 123,45" in resposta and "Fatura de setembro" in resposta


async def test_drive_search_read_le_o_arquivo(client, google, usar_modelo):
    usar_modelo(modelo_que_chama("drive_search_read", {"query": "Plano Q4"}, []))
    _, h = await usuario(client)
    await conectar(client, h)
    cid = (await criar(client, h))["id"]

    await client.post(f"/api/chat/{cid}", json=corpo("resume o arquivo Plano Q4 do meu Drive"), headers=h)

    resposta = await ultima_resposta(client, h, cid)
    assert "lançar o conector em outubro" in resposta
    assert "foto.png" in resposta  # os outros achados vão como lista
    export = next(r for r in google.vistas if r.url.path == "/drive/v3/files/d1/export")
    assert export.url.params["mimeType"] == "text/plain"
    busca = next(r for r in google.vistas if r.url.path == "/drive/v3/files")
    assert "orderBy" not in busca.url.params  # a Drive API recusa orderBy com fullText
    assert "criado 20/09/2026 09:00" in resposta and "modificado 23/09/2026 10:05" in resposta


async def test_drive_query_vazia_lista_recentes_com_datas(client, google, usar_modelo):
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_que_chama("drive_search_read", {"query": " "}, vistos))
    _, h = await usuario(client)
    await conectar(client, h)
    cid = (await criar(client, h))["id"]

    await client.post(f"/api/chat/{cid}", json=corpo("quais os últimos arquivos do meu Drive?"), headers=h)

    [busca] = [r for r in google.vistas if r.url.path.startswith("/drive/v3/files")]
    assert busca.url.params["orderBy"] == "modifiedTime desc"
    assert busca.url.params["q"] == "trashed = false"
    assert "createdTime" in busca.url.params["fields"]
    resposta = await ultima_resposta(client, h, cid)
    assert "Plano Q4" in resposta and "foto.png" in resposta
    assert "criado 20/09/2026 09:00" in resposta and "modificado 23/09/2026 10:05" in resposta
    [drive] = [t for t in vistos[0].function_tools if t.name == "drive_search_read"]
    assert "vazia" in drive.description and "recentes" in drive.description  # lida do banco (ticket 42)


def arquivos_vistos(msgs: list[ModelMessage]) -> list[BinaryContent]:
    """Arquivos que chegaram ao modelo em qualquer parte do request."""
    return [
        c for m in msgs if isinstance(m, ModelRequest) for p in m.parts if isinstance(p, UserPromptPart)
        and not isinstance(p.content, str) for c in p.content if isinstance(c, BinaryContent)
    ]


def modelo_que_le_pdf(pedidos: list[list[ModelMessage]]):
    """Chama drive_search_read no 1º turno; guarda o que cada request recebeu."""

    async def stream(msgs: list[ModelMessage], info: AgentInfo):
        pedidos.append(msgs)
        if len(pedidos) == 1:
            yield {0: DeltaToolCall(name="drive_search_read", json_args='{"query": "guia"}', tool_call_id="c1")}
            return
        feitos = retornos(msgs[-1:])
        yield f"Resposta: {feitos[-1].content}" if feitos else "Sem tool."

    return FunctionModel(stream_function=stream, model_name=MODELO)


async def test_drive_search_read_entrega_pdf_como_arquivo(client, usar_modelo):
    g = Google(arquivos=[GUIA, ARQUIVOS[1]])
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    pedidos: list[list[ModelMessage]] = []
    usar_modelo(modelo_que_le_pdf(pedidos))
    uid, h = await usuario(client)
    try:
        await conectar(client, h)
        cid = (await criar(client, h))["id"]
        await client.post(f"/api/chat/{cid}", json=corpo("lê a guia autorizada"), headers=h)
    finally:
        app.dependency_overrides.pop(transporte_google, None)
        app.dependency_overrides.pop(transporte, None)

    [pdf] = arquivos_vistos(pedidos[1])
    assert pdf.media_type == "application/pdf" and pdf.data == PDF
    assert pdf.vendor_metadata == MEDIA_PDF
    resposta = await ultima_resposta(client, h, cid)
    assert "guia.pdf" in resposta and "foto.png" in resposta
    ev = [e for e in await eventos("tool_call", user_id=uid) if e.payload["tool"] == "drive_search_read"][-1]
    assert ev.payload["mime"] == "application/pdf" and ev.payload["bytes"] == len(PDF)


async def test_drive_search_read_nao_baixa_pdf_acima_do_teto(client, usar_modelo):
    grande = {**GUIA, "size": str(11 * 1024 * 1024)}
    g = Google(arquivos=[grande])
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    pedidos: list[list[ModelMessage]] = []
    usar_modelo(modelo_que_le_pdf(pedidos))
    _, h = await usuario(client)
    try:
        await conectar(client, h)
        cid = (await criar(client, h))["id"]
        await client.post(f"/api/chat/{cid}", json=corpo("lê a guia autorizada"), headers=h)
    finally:
        app.dependency_overrides.pop(transporte_google, None)
        app.dependency_overrides.pop(transporte, None)

    assert not [r for r in g.vistas if r.url.params.get("alt") == "media"]
    assert not arquivos_vistos(pedidos[1])
    assert "10 MB" in await ultima_resposta(client, h, cid)


async def test_drive_search_read_prefere_texto_ao_pdf(client, usar_modelo):
    g = Google(arquivos=[GUIA, ARQUIVOS[0]])
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    pedidos: list[list[ModelMessage]] = []
    usar_modelo(modelo_que_le_pdf(pedidos))
    _, h = await usuario(client)
    try:
        await conectar(client, h)
        cid = (await criar(client, h))["id"]
        await client.post(f"/api/chat/{cid}", json=corpo("lê o plano"), headers=h)
    finally:
        app.dependency_overrides.pop(transporte_google, None)
        app.dependency_overrides.pop(transporte, None)

    assert not [r for r in g.vistas if r.url.params.get("alt") == "media"]
    assert not arquivos_vistos(pedidos[1])
    resposta = await ultima_resposta(client, h, cid)
    assert "lançar o conector em outubro" in resposta and "guia.pdf" in resposta


async def test_pdf_do_drive_nao_volta_no_turno_seguinte(client, usar_modelo):
    g = Google(arquivos=[GUIA])
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    pedidos: list[list[ModelMessage]] = []
    usar_modelo(modelo_que_le_pdf(pedidos))
    _, h = await usuario(client)
    try:
        await conectar(client, h)
        cid = (await criar(client, h))["id"]
        await client.post(f"/api/chat/{cid}", json=corpo("lê a guia autorizada"), headers=h)
        await client.post(f"/api/chat/{cid}", json=corpo("e o valor?"), headers=h)
    finally:
        app.dependency_overrides.pop(transporte_google, None)
        app.dependency_overrides.pop(transporte, None)

    assert arquivos_vistos(pedidos[1])
    assert not arquivos_vistos(pedidos[2])
    assert "[arquivo do Drive: guia.pdf." in str(pedidos[2])
    assert "chame drive_search_read de novo" in str(pedidos[2])
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert "data:application/pdf" not in json.dumps(msgs)
    assert [m["role"] for m in msgs].count("user") == 2  # o PDF não vira Mensagem de usuário


# ---------- Token expirado ----------


async def test_token_expirado_e_renovado_sem_o_usuario_perceber(client, google, usar_modelo):
    usar_modelo(modelo_que_chama("gmail_search", {"query": "fatura"}, []))
    uid, h = await usuario(client)
    await conectar(client, h)
    await expirar(uid)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("meu último e-mail sobre fatura"), headers=h)

    assert r.status_code == 200, r.text
    assert "Fatura de setembro" in await ultima_resposta(client, h, cid)
    refresh = [parse_qs(r.content.decode()) for r in google.vistas if r.url.path == "/token"][-1]
    assert refresh["grant_type"] == ["refresh_token"] and refresh["refresh_token"] == ["refresh-1"]
    assert set(google.bearer("/users/me/messages")) == {"Bearer acesso-2"}
    [c] = (await client.get("/api/connectors", headers=h)).json()
    assert datetime.fromisoformat(c["expira_em"]) > datetime.now(UTC)


async def test_token_expirado_sem_refresh_valido_da_mensagem_clara(client, google, usar_modelo):
    usar_modelo(modelo_que_chama("gmail_search", {"query": "fatura"}, []))
    uid, h = await usuario(client)
    await conectar(client, h)
    await expirar(uid)
    google.refresh_ok = False
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("meu último e-mail sobre fatura"), headers=h)

    assert r.status_code == 200, r.text
    resposta = await ultima_resposta(client, h, cid)
    assert "expirou" in resposta and "Conectores" in resposta
    assert google.bearer("/users/me/messages") == []
    [ev] = await eventos("connector_refresh_failed", user_id=uid)
    assert "invalid_grant" in ev.payload["erro"]
