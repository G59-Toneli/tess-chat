"""Turno em background (ticket 55): desconexão não mata o turno, retomada, 409 e Parar."""

import asyncio
import json
import uuid

import pytest
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app import turnos
from app.chat import MODELO, modelo
from app.credito import CreditLedger
from app.db import SessionLocal
from app.main import app
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_conversas import criar, usuario
from tests.test_resiliencia import chunks


@pytest.fixture
def modelo_com_trava():
    """Modelo que manda "parte 1", espera a trava e manda "parte 2"."""
    trava = asyncio.Event()

    async def stream(_msgs: list[ModelMessage], _info: AgentInfo):
        yield "parte 1 "
        await trava.wait()
        yield "parte 2"

    app.dependency_overrides[modelo] = lambda: FunctionModel(stream_function=stream, model_name=MODELO)
    yield trava
    trava.set()
    app.dependency_overrides.pop(modelo, None)


async def ativo(cid: str) -> turnos.TurnoAtivo:
    """Espera o turno da Conversa entrar no registro e mandar o 1º texto."""
    for _ in range(200):
        t = turnos.ATIVOS.get(uuid.UUID(cid))
        if t and any("text-delta" in c for c in t.chunks):
            return t
        await asyncio.sleep(0.01)
    raise AssertionError("turno não começou")


async def fim(cid: str) -> None:
    for _ in range(500):
        if uuid.UUID(cid) not in turnos.ATIVOS:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("turno não acabou")


async def post_e_desconectar(cid: str, h: dict, body: dict) -> bytes:
    """POST direto no ASGI: depois do 1º texto o cliente some (http.disconnect), como na troca de tela.
    O ASGITransport do httpx só devolve a resposta inteira, então não serve aqui."""
    saiu = asyncio.Event()
    lidos: list[bytes] = []
    pediu = False

    async def receive():
        nonlocal pediu
        if not pediu:
            pediu = True
            return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}
        await saiu.wait()
        return {"type": "http.disconnect"}

    async def send(msg):
        if msg["type"] == "http.response.body":
            lidos.append(msg.get("body", b""))
            if b"text-delta" in b"".join(lidos):
                saiu.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"/api/chat/{cid}",
        "raw_path": f"/api/chat/{cid}".encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json"), (b"authorization", h["Authorization"].encode())],
        "server": ("test", 80),
        "client": ("127.0.0.1", 123),
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=10)
    return b"".join(lidos)


async def test_cliente_sai_no_meio_e_o_turno_termina_gravado_e_cobrado(client, modelo_com_trava):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    lido = await post_e_desconectar(cid, h, corpo("pergunta longa"))
    assert b"parte 1" in lido and b"parte 2" not in lido
    # O cliente já saiu; o turno segue no servidor.
    assert uuid.UUID(cid) in turnos.ATIVOS
    # A pergunta já está no banco antes da resposta.
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user"]

    modelo_com_trava.set()
    await fim(cid)

    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["parts"][-1]["text"] == "parte 1 parte 2"
    async with SessionLocal() as s:
        [linha] = (await s.scalars(select(CreditLedger).where(CreditLedger.user_id == uid))).all()
    assert linha.message_id == msgs[1]["id"] and linha.cost_micro_usd > 0
    [call] = await eventos("llm_call", user_id=uid)
    assert call.payload["message_id"] == msgs[1]["id"]
    [enviada] = await eventos("message_sent", user_id=uid)
    assert enviada.payload["message_id"] == msgs[0]["id"]


async def test_stream_faz_replay_desde_o_inicio_e_204_sem_turno(client, modelo_com_trava):
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    assert (await client.get(f"/api/chat/{cid}/stream", headers=h)).status_code == 204

    post = asyncio.create_task(client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=h))
    await ativo(cid)
    retomada = asyncio.create_task(client.get(f"/api/chat/{cid}/stream", headers=h))
    await asyncio.sleep(0.05)
    modelo_com_trava.set()
    r1, r2 = await post, await retomada

    assert r1.status_code == r2.status_code == 200
    assert r2.headers["x-vercel-ai-ui-message-stream"] == "v1"
    # Quem retoma vê o mesmo stream de quem mandou, começando pelo `start`.
    assert r2.text == r1.text
    assert chunks(r2.text)[0]["type"] == "start"
    assert "parte 1 " in r2.text and "parte 2" in r2.text
    assert (await client.get(f"/api/chat/{cid}/stream", headers=h)).status_code == 204


async def test_segundo_post_com_turno_ativo_da_409(client, modelo_com_trava):
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    post = asyncio.create_task(client.post(f"/api/chat/{cid}", json=corpo("um"), headers=h))
    await ativo(cid)
    r = await client.post(f"/api/chat/{cid}", json=corpo("dois"), headers=h)
    assert r.status_code == 409
    modelo_com_trava.set()
    assert (await post).status_code == 200

    # Acabou o turno: a Conversa aceita o próximo.
    r = await client.post(f"/api/chat/{cid}", json=corpo("três"), headers=h)
    assert r.status_code == 200, r.text
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]


async def test_parar_grava_o_parcial_com_aviso_e_cobra(client, modelo_com_trava):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    assert (await client.post(f"/api/chat/{cid}/parar", headers=h)).status_code == 204

    post = asyncio.create_task(client.post(f"/api/chat/{cid}", json=corpo("fala muito"), headers=h))
    await ativo(cid)
    r = await client.post(f"/api/chat/{cid}/parar", headers=h)
    assert r.status_code == 204
    # O /parar só volta com o parcial gravado.
    assert uuid.UUID(cid) not in turnos.ATIVOS
    stream = (await post).text
    assert "parte 2" not in stream
    [aviso] = [c for c in chunks(stream) if c["type"] == "data-turno-interrompido"]
    assert aviso["data"]["motivo"] == "parado_pelo_usuario"

    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    partes = msgs[1]["parts"]
    assert any(p.get("text") == "parte 1 " for p in partes)
    assert partes[-1]["type"] == "data-turno-interrompido"
    [ev] = await eventos("turn_stopped", user_id=uid)
    assert ev.payload["message_id"] == msgs[1]["id"]
    assert await eventos("llm_call", user_id=uid) == []
    async with SessionLocal() as s:
        [linha] = (await s.scalars(select(CreditLedger).where(CreditLedger.user_id == uid))).all()
    assert (linha.message_id, linha.cost_micro_usd) == (msgs[1]["id"], ev.cost_micro_usd)


async def test_tentar_de_novo_apos_falha_nao_duplica_a_pergunta(client):
    chamadas: list[int] = []

    async def stream(_msgs: list[ModelMessage], _info: AgentInfo):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("quebrou no meio")
        yield "agora foi"

    app.dependency_overrides[modelo] = lambda: FunctionModel(stream_function=stream, model_name=MODELO)
    try:
        _, h = await usuario(client)
        cid = (await criar(client, h))["id"]
        body = corpo("pergunta")
        await client.post(f"/api/chat/{cid}", json=body, headers=h)
        r = await client.post(f"/api/chat/{cid}", json={**body, "trigger": "regenerate-message", "messageId": None}, headers=h)
    finally:
        app.dependency_overrides.pop(modelo, None)

    assert r.status_code == 200, r.text
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["parts"][-1]["text"] == "agora foi"
