"""Chat com streaming (ticket 06). Modelo de teste ou resposta gravada do Gemini."""

import json
import uuid
from pathlib import Path

import httpx2
import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.chat import MODELO, modelo
from app.main import app
from tests.test_auth import eventos
from tests.test_conversas import criar, usuario

GRAVADA = Path(__file__).parent / "fixtures" / "gemini_stream.sse"


def corpo(texto: str, historico: list[dict] | None = None) -> dict:
    """Body do useChat: histórico do front + a mensagem nova."""
    nova = {"id": uuid.uuid4().hex, "role": "user", "parts": [{"type": "text", "text": texto}]}
    return {"trigger": "submit-message", "id": "chat", "messages": [*(historico or []), nova]}


@pytest.fixture
def usar_modelo():
    """Troca o modelo da rota. Limpa o override no fim."""

    def trocar(m):
        app.dependency_overrides[modelo] = lambda: m

    yield trocar
    app.dependency_overrides.pop(modelo, None)


def gemini_falso(status: int, conteudo: bytes, tipo: str) -> GoogleModel:
    """GoogleModel real com HTTP trocado por resposta fixa."""
    transporte = httpx2.MockTransport(
        lambda _req: httpx2.Response(status, content=conteudo, headers={"content-type": tipo})
    )
    provider = GoogleProvider(api_key="teste", http_client=httpx2.AsyncClient(transport=transporte))
    return GoogleModel(MODELO, provider=provider)


def textos(msgs: list[ModelMessage]) -> list[tuple[str, str]]:
    """(tipo, texto) de cada mensagem que o modelo recebeu."""
    saida = []
    for m in msgs:
        for p in m.parts:
            if isinstance(m, ModelRequest) and isinstance(p, UserPromptPart):
                saida.append(("user", p.content))
            elif isinstance(m, ModelResponse) and isinstance(p, TextPart):
                saida.append(("assistant", p.content))
    return saida


async def test_segunda_mensagem_ve_a_primeira(client, usar_modelo):
    vistas: list[list[ModelMessage]] = []

    async def stream(msgs: list[ModelMessage], _info: AgentInfo):
        vistas.append(msgs)
        yield f"resposta {len(vistas)}"

    usar_modelo(FunctionModel(stream_function=stream))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r1 = await client.post(f"/api/chat/{cid}", json=corpo("meu nome é Ana"), headers=h)
    assert r1.status_code == 200, r1.text
    assert "resposta 1" in r1.text
    # O front manda o histórico dele junto; o servidor usa o do banco.
    lixo = [{"id": "x", "role": "user", "parts": [{"type": "text", "text": "histórico falso do front"}]}]
    r2 = await client.post(f"/api/chat/{cid}", json=corpo("qual meu nome?", lixo), headers=h)
    assert r2.status_code == 200, r2.text

    assert textos(vistas[1]) == [
        ("user", "meu nome é Ana"),
        ("assistant", "resposta 1"),
        ("user", "qual meu nome?"),
    ]
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[3]["parts"][-1]["text"] == "resposta 2"


def usage_gravado() -> dict:
    """usageMetadata do último chunk do SSE gravado (é cumulativo)."""
    chunks = [json.loads(l[5:]) for l in GRAVADA.read_text(encoding="utf-8").splitlines() if l.startswith("data:")]
    return chunks[-1]["usageMetadata"]


async def test_tokens_gravados_batem_com_usage_metadata(client, usar_modelo):
    usar_modelo(gemini_falso(200, GRAVADA.read_bytes(), "text/event-stream"))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("pergunta"), headers=h)
    assert r.status_code == 200, r.text

    um = usage_gravado()
    thoughts = um.get("thoughtsTokenCount", 0)
    assistente = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()[-1]
    assert assistente["role"] == "assistant"
    assert assistente["model"] == MODELO
    assert assistente["input_tokens"] == um["promptTokenCount"]
    assert assistente["output_tokens"] == um["candidatesTokenCount"] + thoughts
    assert (assistente["thinking_tokens"] or 0) == thoughts
    assert (assistente["cache_read_tokens"] or 0) == um.get("cachedContentTokenCount", 0)

    [ev] = await eventos("llm_call", user_id=uid)
    assert str(ev.conversation_id) == cid
    assert (ev.input_tokens, ev.output_tokens) == (assistente["input_tokens"], assistente["output_tokens"])
    assert ev.model == MODELO
    assert ev.latency_ms is not None and ev.latency_ms >= 0


async def test_erro_do_provedor_vira_502_e_llm_error(client, usar_modelo):
    erro = {"error": {"code": 503, "message": "The model is overloaded.", "status": "UNAVAILABLE"}}
    usar_modelo(gemini_falso(503, json.dumps(erro).encode(), "application/json"))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=h)

    assert r.status_code == 502
    assert "503" in r.json()["detail"]
    [ev] = await eventos("llm_error", user_id=uid)
    assert str(ev.conversation_id) == cid
    assert ev.model == MODELO
    # Turno que falhou não entra no histórico.
    assert (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json() == []


async def test_conversa_de_outro_usuario_404(client, usar_modelo):
    usar_modelo(FunctionModel(stream_function=lambda _m, _i: _nunca()))
    _, ha = await usuario(client)
    _, hb = await usuario(client)
    cid = (await criar(client, ha))["id"]

    assert (await client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=hb)).status_code == 404
    assert (await client.post(f"/api/chat/{cid}", json=corpo("oi"))).status_code == 401


async def _nunca():
    raise AssertionError("modelo não devia ser chamado")
    yield ""


async def test_ultima_mensagem_precisa_ser_do_usuario(client, usar_modelo):
    usar_modelo(FunctionModel(stream_function=lambda _m, _i: _nunca()))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    body = corpo("oi")
    body["messages"][-1]["role"] = "assistant"

    assert (await client.post(f"/api/chat/{cid}", json=body, headers=h)).status_code == 422
