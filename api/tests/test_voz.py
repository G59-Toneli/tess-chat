"""Ligação (ticket 76): ticket, relay com Gemini falso, vaga de turno, limite, fim único e acerto."""

import asyncio
import base64
import json
import math
import uuid
from contextlib import asynccontextmanager
from fractions import Fraction

import pytest
from google.genai import types
from pydantic_ai.models.function import FunctionModel

from app import turnos, voz
from app.chat import MODELO
from app.config import settings
from app.credito import Cap
from app.db import SessionLocal
from app.main import app
from tests.test_auth import eventos
from tests.test_chat import _nunca, corpo
from tests.test_conversas import criar, usuario
from tests.test_credito import linhas

# Preço de tabela do ADR 0027 em USD por 1M. Pensamento como texto de saída (INFERIDO).
PRECO = {"texto_in": "0.75", "audio_in": "3", "imagem_in": "1", "texto_out": "4.50", "audio_out": "12", "pensamento": "4.50"}


def custo(**tokens: int) -> int:
    return math.ceil(sum(n * Fraction(PRECO[k]) for k, n in tokens.items()))


def uso(texto: int, audio: int, imagem: int, saida: int, pensamento: int) -> types.LiveServerMessage:
    """turn_complete com o usage_metadata do turno, no formato que o spike 75 viu."""
    return types.LiveServerMessage(
        server_content=types.LiveServerContent(turn_complete=True),
        usage_metadata=types.UsageMetadata(
            prompt_tokens_details=[
                types.ModalityTokenCount(modality="TEXT", token_count=texto),
                types.ModalityTokenCount(modality="AUDIO", token_count=audio),
                types.ModalityTokenCount(modality="IMAGE", token_count=imagem),
            ],
            response_tokens_details=[types.ModalityTokenCount(modality="AUDIO", token_count=saida)],
            thoughts_token_count=pensamento,
        ),
    )


def conteudo(**campos) -> types.LiveServerMessage:
    return types.LiveServerMessage(server_content=types.LiveServerContent(**campos))


class GeminiFalso:
    """Sessão Live falsa. `receive()` acaba no turn_complete, como o SDK. `cair()` derruba a sessão."""

    def __init__(self) -> None:
        self.audio: list[bytes] = []
        self.frames: list[bytes] = []
        self.instrucao: str | None = None
        self.fila: asyncio.Queue[types.LiveServerMessage | Exception] = asyncio.Queue()

    async def send_realtime_input(self, *, audio=None, video=None) -> None:
        if audio is not None:
            self.audio.append(audio.data)
        if video is not None:
            self.frames.append(video.data)

    async def receive(self):
        while True:
            m = await self.fila.get()
            if isinstance(m, Exception):
                raise m
            yield m
            if m.server_content and m.server_content.turn_complete:
                return

    def mandar(self, *msgs: types.LiveServerMessage) -> None:
        for m in msgs:
            self.fila.put_nowait(m)

    def cair(self) -> None:
        self.fila.put_nowait(ConnectionError("1011 caiu"))

    def conector(self):
        @asynccontextmanager
        async def abrir(instrucao: str):
            self.instrucao = instrucao
            yield self

        return abrir


@pytest.fixture
def gemini():
    g = GeminiFalso()
    app.dependency_overrides[voz.conectar_gemini] = g.conector
    yield g
    app.dependency_overrides.pop(voz.conectar_gemini, None)


class Browser:
    """Cliente WebSocket direto no ASGI, no mesmo loop do pytest (o pool do asyncpg é do loop)."""

    def __init__(self, ticket: str) -> None:
        self.entrada: asyncio.Queue[dict] = asyncio.Queue()
        self.saida: asyncio.Queue[dict] = asyncio.Queue()
        self.entrada.put_nowait({"type": "websocket.connect"})
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": "/api/voz/ws",
            "raw_path": b"/api/voz/ws",
            "query_string": f"ticket={ticket}".encode(),
            "root_path": "",
            "headers": [],
            "server": ("test", 80),
            "client": ("127.0.0.1", 123),
            "subprotocols": [],
        }
        self.task = asyncio.create_task(app(scope, self.entrada.get, self.saida.put))

    def audio(self, pcm: bytes) -> None:
        self.entrada.put_nowait({"type": "websocket.receive", "bytes": pcm})

    def json(self, dado: dict) -> None:
        self.entrada.put_nowait({"type": "websocket.receive", "text": json.dumps(dado)})

    def cair(self) -> None:
        self.entrada.put_nowait({"type": "websocket.disconnect", "code": 1001})

    async def proxima(self) -> dict:
        """Próxima mensagem do servidor, pulando o accept."""
        while True:
            m = await asyncio.wait_for(self.saida.get(), timeout=5)
            if m["type"] != "websocket.accept":
                return m

    async def texto(self) -> dict:
        m = await self.proxima()
        assert m["type"] == "websocket.send" and m.get("text"), m
        return json.loads(m["text"])

    async def fechamento(self) -> int:
        """Lê até o close e devolve o código. As mensagens lidas ficam em `lidas`."""
        self.lidas: list[dict] = []
        while (m := await self.proxima())["type"] != "websocket.close":
            self.lidas.append(m)
        await asyncio.wait_for(self.task, timeout=5)
        return m["code"]


async def pedir_ticket(client, h: dict, cid: str):
    return await client.post("/api/voz/ticket", json={"conversa_id": cid}, headers=h)


async def ligar(client, h: dict, cid: str) -> Browser:
    r = await pedir_ticket(client, h, cid)
    assert r.status_code == 200, r.text
    assert r.json()["expira_em"] == 30
    b = Browser(r.json()["ticket"])
    assert await b.texto() == {"tipo": "pronto", "limite_s": settings.ligacao_limite_s}
    return b


async def esperar(cond) -> None:
    for _ in range(200):
        if cond():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condição não chegou")


def livre(uid: uuid.UUID, cid: str) -> bool:
    return uid not in voz.LIGACOES and uuid.UUID(cid) not in turnos.ATIVOS


async def test_ticket_invalido_expirado_ou_reusado_fecha_4401(client, gemini, monkeypatch):
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    assert await Browser("nao-existe").fechamento() == 4401

    monkeypatch.setattr(settings, "ligacao_ticket_s", 0)
    expirado = (await pedir_ticket(client, h, cid)).json()["ticket"]
    assert await Browser(expirado).fechamento() == 4401
    monkeypatch.setattr(settings, "ligacao_ticket_s", 30)

    codigo = (await pedir_ticket(client, h, cid)).json()["ticket"]
    b = Browser(codigo)
    assert (await b.texto())["tipo"] == "pronto"
    b.json({"tipo": "desligar"})
    assert await b.fechamento() == 1000
    assert await Browser(codigo).fechamento() == 4401


async def test_sem_espaco_no_cap_recusa_o_ticket_com_402_e_nada_no_ledger(client, gemini):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    async with SessionLocal() as s:
        s.add(Cap(user_id=uid, limite_micro_usd=1000))
        await s.commit()

    r = await pedir_ticket(client, h, cid)

    assert r.status_code == 402, r.text
    [ev] = await eventos("cap_reached", user_id=uid)
    assert ev.model == "gemini-3.8-live"
    assert await linhas(user_id=uid) == []


async def test_segunda_ligacao_e_texto_durante_a_ligacao_dao_409(client, gemini, usar_modelo):
    usar_modelo(FunctionModel(stream_function=lambda _m, _i: _nunca(), model_name=MODELO))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    outra = (await criar(client, h))["id"]
    b = await ligar(client, h, cid)

    assert (await pedir_ticket(client, h, outra)).status_code == 409
    assert (await pedir_ticket(client, h, cid)).status_code == 409
    assert (await client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=h)).status_code == 409

    b.json({"tipo": "desligar"})
    assert await b.fechamento() == 1000
    assert livre(uid, cid)


async def test_teto_global_de_ligacoes_da_429(client, gemini, monkeypatch):
    monkeypatch.setattr(settings, "ligacao_teto_global", 1)
    _, h1 = await usuario(client)
    _, h2 = await usuario(client)
    c1 = (await criar(client, h1))["id"]
    c2 = (await criar(client, h2))["id"]
    b = await ligar(client, h1, c1)

    assert (await pedir_ticket(client, h2, c2)).status_code == 429

    b.json({"tipo": "desligar"})
    assert await b.fechamento() == 1000


async def test_relay_leva_audio_e_frame_e_traz_audio_transcricao_e_interrupcao(client, gemini):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    b = await ligar(client, h, cid)
    assert "recebe imagens dela" in gemini.instrucao

    b.json({"tipo": "tela", "ativa": True})
    b.audio(b"\x01\x02" * 320)
    b.json({"tipo": "frame", "jpeg": base64.b64encode(b"jpeg-1").decode()})
    # Segundo Frame no mesmo segundo: acima de 1 fps, descartado.
    b.json({"tipo": "frame", "jpeg": base64.b64encode(b"jpeg-2").decode()})
    gemini.mandar(
        conteudo(input_transcription=types.Transcription(text="Leia o pedido")),
        conteudo(
            model_turn=types.Content(role="model", parts=[types.Part(inline_data=types.Blob(data=b"pcm-24k", mime_type="audio/pcm;rate=24000"))]),
            output_transcription=types.Transcription(text="O pedido "),
        ),
        conteudo(output_transcription=types.Transcription(text="é 4827")),
        conteudo(interrupted=True),
        uso(400, 300, 264, 100, 50),
    )

    assert await b.texto() == {"tipo": "transcricao", "origem": "usuario", "texto": "Leia o pedido", "final": True}
    assert (await b.proxima())["bytes"] == b"pcm-24k"
    assert await b.texto() == {"tipo": "transcricao", "origem": "agente", "texto": "O pedido ", "final": False}
    assert await b.texto() == {"tipo": "transcricao", "origem": "agente", "texto": "O pedido é 4827", "final": False}
    assert await b.texto() == {"tipo": "interrompido"}
    assert await b.texto() == {"tipo": "transcricao", "origem": "agente", "texto": "O pedido é 4827", "final": True}
    b.json({"tipo": "tela", "ativa": False})
    await esperar(lambda: gemini.frames)
    assert gemini.audio == [b"\x01\x02" * 320]
    assert gemini.frames == [b"jpeg-1"]

    b.json({"tipo": "desligar"})
    assert await b.fechamento() == 1000
    assert len(await eventos("screen_share_started", user_id=uid)) == 1
    assert len(await eventos("screen_share_stopped", user_id=uid)) == 1
    assert livre(uid, cid)


async def test_limite_encerra_com_fim_limite_e_libera_a_vaga(client, gemini, monkeypatch):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    monkeypatch.setattr(settings, "ligacao_limite_s", 0.2)
    b = await ligar(client, h, cid)

    assert await b.fechamento() == 1000
    assert json.loads(b.lidas[-1]["text"]) == {"tipo": "fim", "motivo": "limite"}
    assert livre(uid, cid)
    [ev] = await eventos("voice_call_ended", user_id=uid)
    assert ev.payload["motivo"] == "limite"


async def test_desligar_soma_os_turnos_no_ledger_e_audita_o_fim(client, gemini):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    b = await ligar(client, h, cid)
    gemini.mandar(uso(464, 330, 264, 195, 87), uso(494, 547, 264, 218, 80))
    await asyncio.sleep(0.05)

    b.json({"tipo": "desligar"})
    assert await b.fechamento() == 1000

    assert json.loads(b.lidas[-1]["text"]) == {"tipo": "fim", "motivo": "desligou"}
    esperado = custo(texto_in=958, audio_in=877, imagem_in=528, audio_out=413, pensamento=167)
    [linha] = await linhas(user_id=uid)
    assert linha.model == "gemini-3.8-live" and linha.conversation_id == uuid.UUID(cid)
    assert linha.cost_micro_usd == esperado
    assert (linha.input_tokens, linha.output_tokens, linha.thinking_tokens) == (958 + 877 + 528, 413 + 167, 167)
    [ev] = await eventos("voice_call_ended", user_id=uid)
    assert ev.payload["motivo"] == "desligou"
    assert ev.payload["tokens"] == {"texto_in": 958, "audio_in": 877, "imagem_in": 528, "texto_out": 0, "audio_out": 413, "pensamento": 167}
    assert ev.cost_micro_usd == esperado
    assert len(await eventos("voice_call_started", user_id=uid)) == 1
    assert livre(uid, cid)


async def test_queda_do_browser_acerta_e_libera_a_vaga(client, gemini):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    b = await ligar(client, h, cid)
    gemini.mandar(uso(100, 200, 0, 50, 10))
    await asyncio.sleep(0.05)

    b.cair()
    await asyncio.wait_for(b.task, timeout=5)

    [linha] = await linhas(user_id=uid)
    assert linha.cost_micro_usd == custo(texto_in=100, audio_in=200, audio_out=50, pensamento=10)
    [ev] = await eventos("voice_call_ended", user_id=uid)
    assert ev.payload["motivo"] == "queda"
    assert livre(uid, cid)


async def test_queda_do_gemini_manda_erro_e_fim_erro(client, gemini):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    b = await ligar(client, h, cid)

    gemini.cair()

    assert await b.fechamento() == 1000
    assert [json.loads(m["text"])["tipo"] for m in b.lidas] == ["erro", "fim"]
    assert json.loads(b.lidas[-1]["text"])["motivo"] == "erro"
    [ev] = await eventos("voice_call_ended", user_id=uid)
    assert ev.payload["estimado"] is True
    assert livre(uid, cid)


async def test_gemini_que_nao_abre_fecha_4500_e_libera_a_vaga(client):
    @asynccontextmanager
    async def falha(_instrucao: str):
        raise ConnectionError("sem chave")
        yield

    app.dependency_overrides[voz.conectar_gemini] = lambda: falha
    try:
        uid, h = await usuario(client)
        cid = (await criar(client, h))["id"]
        ticket = (await pedir_ticket(client, h, cid)).json()["ticket"]
        assert await Browser(ticket).fechamento() == 4500
    finally:
        app.dependency_overrides.pop(voz.conectar_gemini, None)
    assert livre(uid, cid)
    assert await eventos("voice_call_ended", user_id=uid) == []
