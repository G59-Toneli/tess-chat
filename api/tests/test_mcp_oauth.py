"""Servidor MCP por OAuth (ticket 52, ADR 0022). MockTransport faz o auth server; o mcp-demo real serve as tools."""

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from importlib import import_module
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import text

from app.conectores import _cifrar, _decifrar
from app.db import SessionLocal
from app.main import app
from app.mcp_oauth import CALLBACK, transporte_mcp_oauth
from app.tools import transporte
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_conectores import modelo_que_chama, ultima_resposta
from tests.test_conversas import criar, usuario
from tests.test_mcp import SERVIDOR, TOKEN, porta_livre

AS = "https://8.8.8.8"  # IP público literal: passa no validar_url sem DNS; o MockTransport atende
CLIENT_ID = "cli-dcr-1"


class AuthServer:
    """Auth server OAuth falso: 401 do MCP, metadata RFC 9728 e 8414, DCR e /token."""

    def __init__(self, mcp_url: str) -> None:
        self.mcp_url = mcp_url
        self.as_url = AS
        self.metadata_extra: dict[str, str] = {}
        self.com_dcr = True
        self.access = TOKEN  # o mcp-demo só aceita esse Bearer
        self.refresh_status = 200
        self.vistas: list[httpx.Request] = []

    def formularios(self, grant: str) -> list[dict[str, str]]:
        fs = [{k: v[0] for k, v in parse_qs(r.content.decode()).items()} for r in self.vistas if r.url.path == "/token"]
        return [f for f in fs if f.get("grant_type") == grant]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.vistas.append(request)
        caminho = request.url.path
        if str(request.url) == self.mcp_url:
            meta = f'{AS}/.well-known/oauth-protected-resource/mcp'
            return httpx.Response(401, headers={"WWW-Authenticate": f'Bearer resource_metadata="{meta}"'})
        if caminho == "/.well-known/oauth-protected-resource/mcp":
            return httpx.Response(200, json={"resource": self.mcp_url, "authorization_servers": [self.as_url]})
        if caminho == "/.well-known/oauth-authorization-server":
            meta = {
                "issuer": AS,
                "authorization_endpoint": f"{AS}/authorize",
                "token_endpoint": f"{AS}/token",
                "response_types_supported": ["code"],
                "code_challenge_methods_supported": ["S256"],
            }
            if self.com_dcr:
                meta["registration_endpoint"] = f"{AS}/register"
            return httpx.Response(200, json={**meta, **self.metadata_extra})
        if caminho == "/register":
            corpo_dcr = json.loads(request.content)
            return httpx.Response(201, json={**corpo_dcr, "client_id": CLIENT_ID})
        if caminho == "/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            if form["grant_type"] == "refresh_token":
                if self.refresh_status != 200:
                    return httpx.Response(self.refresh_status, json={"error": "invalid_grant"})
                return httpx.Response(200, json={"access_token": self.access, "token_type": "Bearer", "expires_in": 3600})
            return httpx.Response(
                200,
                json={"access_token": self.access, "token_type": "Bearer", "expires_in": 3600, "refresh_token": "r1"},
            )
        return httpx.Response(404)


@pytest.fixture
def auth(demo):
    """O mesmo MockTransport nas rotas OAuth e no turno do chat."""
    a = AuthServer(demo)
    mt = httpx.MockTransport(a)
    app.dependency_overrides[transporte_mcp_oauth] = lambda: mt
    app.dependency_overrides[transporte] = lambda: mt
    yield a
    app.dependency_overrides.pop(transporte_mcp_oauth, None)
    app.dependency_overrides.pop(transporte, None)


async def iniciar(client, h, url: str, nome: str = "notion", sid: str | None = None):
    return await client.post("/api/mcp-servers/oauth/iniciar", json={"nome": nome, "url": url, "sid": sid}, headers=h)


def query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


async def conectar(client, h, auth: AuthServer) -> str:
    """Faz iniciar + callback e devolve o id do servidor."""
    r = await iniciar(client, h, auth.mcp_url)
    assert r.status_code == 200, r.text
    q = query(r.json()["url"])
    cb = await client.get(CALLBACK, params={"code": "code-1", "state": q["state"]})
    assert cb.headers["location"].endswith("/mcp?conectado=1"), cb.headers.get("location")
    return (await por_nome(client, h, "notion"))["id"]


async def servidor(client, h, sid: str) -> dict:
    return next(s for s in (await client.get("/api/mcp-servers", headers=h)).json() if s["id"] == sid)


async def por_nome(client, h, nome: str) -> dict:
    return next(s for s in (await client.get("/api/mcp-servers", headers=h)).json() if s["nome"] == nome)


async def linhas() -> int:
    async with SessionLocal() as s:
        return await s.scalar(text("SELECT count(*) FROM mcp_servers"))


async def vencer(sid: str, header: str = "Bearer velho") -> None:
    """Token vencido há 5 min, com outro access no header gravado."""
    async with SessionLocal() as s:
        oauth = _decifrar(await s.scalar(text("SELECT oauth FROM mcp_servers WHERE id = :i"), {"i": sid}))
        oauth["expires_at"] = int(time.time()) - 300
        await s.execute(
            text("UPDATE mcp_servers SET oauth = :o, headers = :h WHERE id = :i"),
            {"o": _cifrar(oauth), "h": _cifrar({"Authorization": header}), "i": sid},
        )
        await s.commit()


async def header_gravado(sid: str) -> str:
    async with SessionLocal() as s:
        return _decifrar(await s.scalar(text("SELECT headers FROM mcp_servers WHERE id = :i"), {"i": sid}))[
            "Authorization"
        ]


# ---------- iniciar ----------


async def test_iniciar_devolve_authorize_com_pkce_resource_e_client_id_do_dcr(client, auth):
    uid, h = await usuario(client)
    antes = await linhas()

    r = await iniciar(client, h, auth.mcp_url)

    assert r.status_code == 200, r.text
    assert r.json()["modo"] == "oauth"
    url = urlparse(r.json()["url"])
    q = query(r.json()["url"])
    assert f"{url.scheme}://{url.netloc}{url.path}" == f"{AS}/authorize"
    assert q["client_id"] == CLIENT_ID and q["response_type"] == "code"
    assert q["code_challenge_method"] == "S256" and len(q["code_challenge"]) >= 43
    assert q["resource"] == auth.mcp_url
    assert q["redirect_uri"].endswith("/api/mcp-servers/oauth/callback")
    [dcr] = [json.loads(v.content) for v in auth.vistas if v.url.path == "/register"]
    assert dcr["token_endpoint_auth_method"] == "none"
    assert set(dcr["grant_types"]) == {"authorization_code", "refresh_token"}
    assert await linhas() == antes
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and f"path={CALLBACK}" in cookie and "samesite=lax" in cookie
    [ev] = await eventos("mcp_oauth_started", user_id=uid)
    assert ev.payload["nome"] == "notion" and ev.payload["servidor"] is None


async def test_servidor_sem_dcr_pede_token_e_nao_cria_linha(client, auth):
    _, h = await usuario(client)
    auth.com_dcr = False

    r = await iniciar(client, h, auth.mcp_url)

    assert r.status_code == 200 and r.json() == {"modo": "token"}
    assert not [v for v in auth.vistas if v.url.path == "/register"]
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []


async def test_servidor_com_401_sem_metadata_pede_token(client, demo):
    """O mcp-demo com token responde 401 sem WWW-Authenticate e 404 nos well-known."""
    _, h = await usuario(client)

    r = await iniciar(client, h, demo, nome="demo")

    assert r.status_code == 200 and r.json() == {"modo": "token"}
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []
    cad = await client.post("/api/mcp-servers", json={"nome": "demo", "url": demo, "autorizacao": TOKEN}, headers=h)
    assert cad.status_code == 201 and len(cad.json()["tools"]) == 3


@pytest.fixture
def demo_aberto():
    """mcp-demo sem MCP_DEMO_TOKEN: o initialize sem header responde OK."""
    porta = porta_livre()
    env = {k: v for k, v in os.environ.items() if k != "MCP_DEMO_TOKEN"} | {"PORT": str(porta)}
    proc = subprocess.Popen([sys.executable, str(SERVIDOR)], env=env)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", porta), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("servidor demo não subiu")
        yield f"http://127.0.0.1:{porta}/mcp"
    finally:
        proc.terminate()
        proc.wait(5)


async def test_servidor_sem_auth_devolve_sem_auth_e_o_post_sem_header_cadastra(client, demo_aberto):
    uid, h = await usuario(client)

    r = await iniciar(client, h, demo_aberto, nome="aberto")

    assert r.status_code == 200 and r.json() == {"modo": "sem_auth"}
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []
    assert not await eventos("mcp_oauth_started", user_id=uid)
    cad = await client.post("/api/mcp-servers", json={"nome": "aberto", "url": demo_aberto, "autorizacao": None}, headers=h)
    assert cad.status_code == 201 and cad.json()["tem_auth"] is False and len(cad.json()["tools"]) == 3


async def test_url_fora_do_ar_recebe_502(client):
    _, h = await usuario(client)

    r = await iniciar(client, h, f"http://127.0.0.1:{porta_livre()}/mcp")

    assert r.status_code == 502 and "modo" not in r.json()
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []


async def test_url_interna_continua_recusada(client):
    _, h = await usuario(client)

    r = await iniciar(client, h, "https://10.0.0.7/mcp")

    assert r.status_code == 422 and "endereço interno" in r.json()["detail"]
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []


@pytest.mark.parametrize(
    "interna",
    [
        {"as_url": "https://10.0.0.5"},
        {"registration_endpoint": "https://169.254.169.254/register"},
        {"token_endpoint": "https://127.0.0.2/token"},
    ],
)
async def test_metadata_apontando_para_ip_interno_e_recusado(client, auth, interna):
    _, h = await usuario(client)
    if "as_url" in interna:
        auth.as_url = interna["as_url"]
    else:
        auth.metadata_extra = interna

    r = await iniciar(client, h, auth.mcp_url)

    assert r.status_code == 422 and "endereço interno" in r.json()["detail"]
    assert not [v for v in auth.vistas if v.url.host in {"10.0.0.5", "169.254.169.254", "127.0.0.2"}]
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []


# ---------- callback ----------


async def test_callback_liga_o_servidor_com_as_tools_do_demo(client, auth):
    uid, h = await usuario(client)
    r = await iniciar(client, h, auth.mcp_url)
    q = query(r.json()["url"])

    cb = await client.get(CALLBACK, params={"code": "code-1", "state": q["state"]})

    assert cb.status_code == 303 and cb.headers["location"].endswith("/mcp?conectado=1")
    assert "max-age=0" in cb.headers["set-cookie"].lower()
    [troca] = auth.formularios("authorization_code")
    desafio = base64.urlsafe_b64encode(hashlib.sha256(troca["code_verifier"].encode()).digest()).decode().rstrip("=")
    assert desafio == q["code_challenge"]
    assert troca["resource"] == auth.mcp_url and troca["client_id"] == CLIENT_ID and troca["code"] == "code-1"
    srv = await por_nome(client, h, "notion")
    assert srv["estado"] == "ok" and srv["ativo"] is True and srv["tem_auth"] is True
    assert any(t["nome"].endswith("_somar") for t in srv["tools"]) and len(srv["tools"]) == 3
    assert await header_gravado(srv["id"]) == f"Bearer {TOKEN}"
    [ligado] = await eventos("mcp_oauth_linked", user_id=uid)
    [added] = await eventos("mcp_server_added", user_id=uid)
    assert added.payload["tem_auth"] is True and TOKEN not in str(ligado.payload) + str(added.payload)


async def test_callback_sem_cookie_volta_com_pkce_ausente(client, auth):
    _, h = await usuario(client)
    q = query((await iniciar(client, h, auth.mcp_url)).json()["url"])
    client.cookies.clear()

    cb = await client.get(CALLBACK, params={"code": "code-1", "state": q["state"]})

    assert cb.headers["location"].endswith("/mcp?erro=pkce_ausente")
    assert not auth.formularios("authorization_code")
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []


async def test_callback_com_cookie_de_outro_fluxo_volta_com_erro_e_nao_cria_nada(client, auth):
    _, h = await usuario(client)
    primeiro = query((await iniciar(client, h, auth.mcp_url)).json()["url"])
    await iniciar(client, h, auth.mcp_url, nome="outro")  # o cookie agora é do segundo fluxo

    cb = await client.get(CALLBACK, params={"code": "code-1", "state": primeiro["state"]})

    assert cb.headers["location"].endswith("/mcp?erro=state_invalido")
    assert not auth.formularios("authorization_code")
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []


async def test_callback_com_state_adulterado_volta_com_state_invalido(client, auth):
    _, h = await usuario(client)
    q = query((await iniciar(client, h, auth.mcp_url)).json()["url"])

    cb = await client.get(CALLBACK, params={"code": "code-1", "state": q["state"][:-3] + "abc"})

    assert cb.headers["location"].endswith("/mcp?erro=state_invalido")
    assert not auth.formularios("authorization_code")


async def test_callback_com_token_que_o_servidor_recusa_marca_expirado(client, auth):
    _, h = await usuario(client)
    auth.access = "token-que-o-demo-recusa"
    r = await iniciar(client, h, auth.mcp_url)

    cb = await client.get(CALLBACK, params={"code": "code-1", "state": query(r.json()["url"])["state"]})

    assert cb.headers["location"].endswith("/mcp?erro=listagem_falhou")
    srv = await por_nome(client, h, "notion")
    assert srv["estado"] == "expirado" and srv["tools"] == []


async def test_reconectar_reaproveita_a_linha_do_servidor(client, auth):
    _, h = await usuario(client)
    sid = await conectar(client, h, auth)

    r = await iniciar(client, h, auth.mcp_url, sid=sid)
    await client.get(CALLBACK, params={"code": "code-2", "state": query(r.json()["url"])["state"]})

    lista = (await client.get("/api/mcp-servers", headers=h)).json()
    assert [s["id"] for s in lista] == [sid] and len(lista[0]["tools"]) == 3 and lista[0]["estado"] == "ok"


async def test_reconectar_abandonado_deixa_o_servidor_como_estava(client, auth):
    _, h = await usuario(client)
    sid = await conectar(client, h, auth)
    antes = await servidor(client, h, sid)

    r = await iniciar(client, h, auth.mcp_url, sid=sid)  # o usuário fecha a tela do provedor

    assert r.json()["modo"] == "oauth"
    depois = await servidor(client, h, sid)
    assert (depois["estado"], depois["ativo"]) == (antes["estado"], antes["ativo"]) == ("ok", True)
    assert await header_gravado(sid) == f"Bearer {TOKEN}"


async def test_nome_repetido_recebe_409_no_iniciar(client, auth):
    _, h = await usuario(client)
    await conectar(client, h, auth)

    r = await iniciar(client, h, auth.mcp_url)

    assert r.status_code == 409


# ---------- Migração 0022 ----------


async def test_migracao_0022_apaga_pendente_sem_tools_e_mantem_ok(client):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    uid, _ = await usuario(client)
    pendente, ok = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as s:
        for i, estado in ((pendente, "aguardando_oauth"), (ok, "ok")):
            await s.execute(
                text("INSERT INTO mcp_servers (id, user_id, nome, url, headers, ativo, estado) "
                     "VALUES (:i, :u, :n, 'https://8.8.8.8/mcp', :h, false, :e)"),
                {"i": i, "u": uid, "n": estado, "h": _cifrar({}), "e": estado},
            )
        await s.commit()
        conn = await s.connection()

        def rodar(sync):
            with Operations.context(MigrationContext.configure(sync)):
                import_module("migrations.versions.0022_mcp_sem_pendentes").upgrade()

        await conn.run_sync(rodar)
        await s.commit()
        restam = (await s.scalars(text("SELECT id FROM mcp_servers WHERE user_id = :u"), {"u": uid})).all()
    assert restam == [ok]


# ---------- Turno ----------


async def test_token_vencido_renova_antes_do_turno_e_o_header_muda(client, auth, usar_modelo):
    uid, h = await usuario(client)
    sid = await conectar(client, h, auth)
    somar = next(t["nome"] for t in (await servidor(client, h, sid))["tools"] if t["nome"].endswith("_somar"))
    await vencer(sid)
    usar_modelo(modelo_que_chama(somar, {"a": 2, "b": 3}, []))
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("quanto é 2 + 3?"), headers=h)

    assert r.status_code == 200, r.text
    assert await ultima_resposta(client, h, cid) == "Resposta: 5.0"
    assert await header_gravado(sid) == f"Bearer {TOKEN}"
    [renova] = auth.formularios("refresh_token")
    assert renova["refresh_token"] == "r1" and renova["resource"] == auth.mcp_url
    assert await eventos("mcp_oauth_refreshed", user_id=uid)


async def test_refresh_recusado_marca_expirado_e_tira_o_servidor_do_turno(client, auth, usar_modelo):
    uid, h = await usuario(client)
    sid = await conectar(client, h, auth)
    somar = next(t["nome"] for t in (await servidor(client, h, sid))["tools"] if t["nome"].endswith("_somar"))
    await vencer(sid, header=f"Bearer {TOKEN}")  # o header ainda funcionaria: quem tira é o estado
    auth.refresh_status = 400
    vistos = []
    usar_modelo(modelo_que_chama(somar, {"a": 2, "b": 3}, vistos))
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("quanto é 2 + 3?"), headers=h)

    assert r.status_code == 200, r.text
    assert not {t.name for t in vistos[0].function_tools} & {t["nome"] for t in (await servidor(client, h, sid))["tools"]}
    assert (await servidor(client, h, sid))["estado"] == "expirado"
    [ev] = await eventos("mcp_oauth_refresh_failed", user_id=uid)
    assert ev.payload["servidor"] == sid
