"""Cliente MCP (ticket 17). Servidor real: deploy/mcp-demo/server.py em subprocesso, com token."""

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app.db import SessionLocal
from app.tools import Tool
from tests.test_auth import eventos
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_conectores import conectar, google, modelo_que_chama, ultima_resposta  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario

SERVIDOR = Path(__file__).resolve().parents[2] / "deploy" / "mcp-demo" / "server.py"
TOKEN = "segredo-demo"


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def demo():
    """Sobe o servidor demo com token e devolve a URL do /mcp."""
    porta = porta_livre()
    env = {**os.environ, "PORT": str(porta), "MCP_DEMO_TOKEN": TOKEN}
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


async def cadastrar(client, h, url: str, nome: str = "demo", autorizacao: str | None = TOKEN):
    return await client.post("/api/mcp-servers", json={"nome": nome, "url": url, "autorizacao": autorizacao}, headers=h)


async def contagens(uid: uuid.UUID) -> tuple[int, int]:
    async with SessionLocal() as s:
        servidores = await s.scalar(text("SELECT count(*) FROM mcp_servers WHERE user_id = :u"), {"u": uid})
        tools = await s.scalar(select(func.count()).select_from(Tool))
    return servidores, tools


def nomes(r) -> set[str]:
    return {t["nome"] for t in r.json()}


# ---------- Cadastro ----------


async def test_cadastro_lista_tools_e_guarda_header_cifrado(client, demo):
    uid, h = await usuario(client)

    r = await cadastrar(client, h, demo)

    assert r.status_code == 201, r.text
    srv = r.json()
    registradas = {t["nome"] for t in srv["tools"]}
    assert len(registradas) == 2
    assert any(n.endswith("_somar") for n in registradas)
    assert any(n.endswith("_hora_atual") for n in registradas)
    assert srv["tem_auth"] is True and "autorizacao" not in srv
    lista = (await client.get("/api/mcp-servers", headers=h)).json()
    assert [s["id"] for s in lista] == [srv["id"]]
    async with SessionLocal() as s:
        guardado = await s.scalar(text("SELECT headers FROM mcp_servers WHERE id = :i"), {"i": srv["id"]})
    assert TOKEN not in guardado
    [ev] = await eventos("mcp_server_added", user_id=uid)
    assert ev.payload["url"] == demo and ev.payload["tools"] == 2 and TOKEN not in str(ev.payload)


async def test_servidor_fora_do_ar_da_erro_legivel_e_nao_grava(client):
    uid, h = await usuario(client)
    antes = await contagens(uid)

    r = await cadastrar(client, h, f"http://127.0.0.1:{porta_livre()}/mcp")

    assert r.status_code == 502
    assert "Não foi possível conectar" in r.json()["detail"]
    assert await contagens(uid) == antes


async def test_token_errado_da_erro_legivel_e_nao_grava(client, demo):
    uid, h = await usuario(client)
    antes = await contagens(uid)

    r = await cadastrar(client, h, demo, autorizacao="errado")

    assert r.status_code == 502 and "Não foi possível conectar" in r.json()["detail"]
    assert await contagens(uid) == antes


async def test_url_sem_http_e_recusada(client):
    _, h = await usuario(client)
    r = await cadastrar(client, h, "file:///etc/passwd")
    assert r.status_code == 422


async def test_nome_repetido_do_mesmo_usuario_da_409(client, demo):
    _, h = await usuario(client)
    assert (await cadastrar(client, h, demo)).status_code == 201
    assert (await cadastrar(client, h, demo)).status_code == 409


# ---------- Registro por Conversa ----------


async def test_tools_mcp_so_aparecem_para_o_dono(client, demo):
    _, h_dono = await usuario(client)
    _, h_outro = await usuario(client)
    registradas = {t["nome"] for t in (await cadastrar(client, h_dono, demo)).json()["tools"]}
    cid_dono = (await criar(client, h_dono))["id"]
    cid_outro = (await criar(client, h_outro))["id"]

    da_conversa = (await client.get(f"/api/conversations/{cid_dono}/tools", headers=h_dono)).json()
    assert {t["nome"] for t in da_conversa if t["origem"] == "mcp"} == registradas
    assert all(t["servidor"] == "demo" for t in da_conversa if t["origem"] == "mcp")
    assert registradas <= nomes(await client.get("/api/tools", headers=h_dono))
    assert not registradas & nomes(await client.get(f"/api/conversations/{cid_outro}/tools", headers=h_outro))
    assert not registradas & nomes(await client.get("/api/tools", headers=h_outro))


async def test_quem_tem_conector_google_nao_ve_tools_mcp_alheias(client, demo, google):
    _, h_dono = await usuario(client)
    _, h_outro = await usuario(client)
    registradas = {t["nome"] for t in (await cadastrar(client, h_dono, demo)).json()["tools"]}
    await conectar(client, h_outro)
    cid_outro = (await criar(client, h_outro))["id"]

    vistas = nomes(await client.get(f"/api/conversations/{cid_outro}/tools", headers=h_outro))

    assert "gmail_search" in vistas and not registradas & vistas


async def test_turno_chama_tool_mcp_e_audita_com_origem(client, demo, usar_modelo):
    uid, h = await usuario(client)
    tools = (await cadastrar(client, h, demo)).json()["tools"]
    somar = next(t["nome"] for t in tools if t["nome"].endswith("_somar"))
    usar_modelo(modelo_que_chama(somar, {"a": 2, "b": 3}, []))
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("quanto é 2 + 3?"), headers=h)

    assert r.status_code == 200, r.text
    assert await ultima_resposta(client, h, cid) == "Resposta: 5.0"
    [ev] = await eventos("tool_call", user_id=uid)
    assert ev.payload["tool"] == somar and ev.payload["origem"] == "mcp"


async def test_toggle_da_conversa_esconde_tool_mcp_do_modelo(client, demo, usar_modelo):
    _, h = await usuario(client)
    tools = (await cadastrar(client, h, demo)).json()["tools"]
    somar = next(t["nome"] for t in tools if t["nome"].endswith("_somar"))
    vistos = []
    usar_modelo(modelo_que_chama(somar, {"a": 2, "b": 3}, vistos))
    cid = (await criar(client, h))["id"]
    await client.put(f"/api/conversations/{cid}/tools", json={somar: False}, headers=h)

    await client.post(f"/api/chat/{cid}", json=corpo("quanto é 2 + 3?"), headers=h)

    vistas = {t.name for t in vistos[0].function_tools}
    assert somar not in vistas and any(n.endswith("_hora_atual") for n in vistas)


async def test_servidor_desativado_some_das_conversas(client, demo):
    _, h = await usuario(client)
    srv = (await cadastrar(client, h, demo)).json()
    cid = (await criar(client, h))["id"]

    r = await client.put(f"/api/mcp-servers/{srv['id']}", json={"ativo": False}, headers=h)

    assert r.status_code == 200 and r.json()["ativo"] is False
    tools = (await client.get(f"/api/conversations/{cid}/tools", headers=h)).json()
    assert not [t for t in tools if t["origem"] == "mcp"]


async def test_remover_apaga_servidor_e_tools(client, demo):
    uid, h = await usuario(client)
    srv = (await cadastrar(client, h, demo)).json()
    registradas = {t["nome"] for t in srv["tools"]}
    _, h_outro = await usuario(client)

    assert (await client.delete(f"/api/mcp-servers/{srv['id']}", headers=h_outro)).status_code == 404
    r = await client.delete(f"/api/mcp-servers/{srv['id']}", headers=h)

    assert r.status_code == 204
    assert not registradas & nomes(await client.get("/api/tools", headers=h))
    assert (await client.get("/api/mcp-servers", headers=h)).json() == []
    [ev] = await eventos("mcp_server_removed", user_id=uid)
    assert ev.payload["nome"] == "demo"
