"""Retry, fallback de modelo e observabilidade do turno (ticket 06b, ADR 0012)."""

import json

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from sqlalchemy import select

from app.chat import MODELO, MODELO_RESERVA, modelo_reserva
from app.credito import CreditLedger, PrecoModelo
from app.db import SessionLocal
from app.main import app
from tests.test_auth import eventos
from tests.test_chat import GRAVADA, corpo, gemini_falso, usar_modelo  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario
from tests.test_tools import Rotas, usar_rotas  # noqa: F401  (fixture)


@pytest.fixture
def usar_reserva():
    def trocar(m):
        app.dependency_overrides[modelo_reserva] = lambda: m

    yield trocar
    app.dependency_overrides[modelo_reserva] = lambda: None


def falha_n_vezes(n: int, status: int, nome: str = MODELO) -> tuple[FunctionModel, list[int]]:
    """Modelo que levanta `status` nas n primeiras chamadas e depois responde."""
    chamadas: list[int] = []

    async def stream(_msgs: list[ModelMessage], _info: AgentInfo):
        chamadas.append(1)
        if len(chamadas) <= n:
            raise ModelHTTPError(status, nome, {"error": {"code": status}})
        yield f"ok na {len(chamadas)}ª"

    return FunctionModel(stream_function=stream, model_name=nome), chamadas


async def turno(client) -> tuple:
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    r = await client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=h)
    return uid, h, cid, r


async def test_dois_503_e_responde_na_terceira(client, usar_modelo):
    m, chamadas = falha_n_vezes(2, 503)
    usar_modelo(m)

    uid, h, cid, r = await turno(client)

    assert r.status_code == 200, r.text
    assert "ok na 3ª" in r.text
    assert len(chamadas) == 3
    retries = await eventos("llm_retry", user_id=uid)
    assert len(retries) == 2
    assert {e.payload["status"] for e in retries} == {503}
    assert sorted(e.payload["tentativa"] for e in retries) == [1, 2]
    [call] = await eventos("llm_call", user_id=uid)
    assert call.payload["tentativas"] == 3
    assert call.payload["modelo_pedido"] == MODELO
    assert call.payload["modelo_respondido"] == MODELO
    assert await eventos("llm_fallback", user_id=uid) == []


async def test_primeiro_falha_sempre_e_o_segundo_responde(client, usar_modelo, usar_reserva):
    primario, chamadas = falha_n_vezes(99, 503)
    reserva, _ = falha_n_vezes(0, 503, MODELO_RESERVA)
    usar_modelo(primario)
    usar_reserva(reserva)

    uid, h, cid, r = await turno(client)

    assert r.status_code == 200, r.text
    assert "ok na 1ª" in r.text
    assert len(chamadas) == 3
    [fb] = await eventos("llm_fallback", user_id=uid)
    assert (fb.payload["de"], fb.payload["para"]) == (MODELO, MODELO_RESERVA)
    [call] = await eventos("llm_call", user_id=uid)
    assert call.model == MODELO_RESERVA
    assert call.payload["modelo_pedido"] == MODELO
    assert call.payload["tentativas"] == 4

    assistente = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()[-1]
    assert assistente["model"] == MODELO_RESERVA
    async with SessionLocal() as s:
        [linha] = (await s.scalars(select(CreditLedger).where(CreditLedger.user_id == uid))).all()
        preco = await s.get(PrecoModelo, linha.price_id)
    assert linha.model == MODELO_RESERVA
    assert preco.model == MODELO_RESERVA


async def test_400_nao_repete_nem_troca_de_modelo(client, usar_modelo, usar_reserva):
    primario, chamadas = falha_n_vezes(99, 400)
    reserva, chamadas_reserva = falha_n_vezes(0, 503, MODELO_RESERVA)
    usar_modelo(primario)
    usar_reserva(reserva)

    uid, _h, _cid, r = await turno(client)

    assert r.status_code == 502
    assert "400" in r.json()["detail"]
    assert len(chamadas) == 1
    assert chamadas_reserva == []
    assert await eventos("llm_retry", user_id=uid) == []
    assert await eventos("llm_fallback", user_id=uid) == []
    [erro] = await eventos("llm_error", user_id=uid)
    assert erro.payload["tentativas"] == 1


async def test_llm_call_traz_latencia_do_primeiro_token_e_total(client, usar_modelo):
    usar_modelo(gemini_falso(200, GRAVADA.read_bytes(), "text/event-stream"))

    uid, _h, _cid, r = await turno(client)

    assert r.status_code == 200, r.text
    [call] = await eventos("llm_call", user_id=uid)
    ttft = call.payload["latencia_primeiro_token_ms"]
    assert isinstance(ttft, int) and 0 <= ttft <= call.latency_ms
    assert call.payload["motivo_termino"] == "stop"


async def test_teto_de_tool_calls_corta_o_turno(client, usar_modelo, usar_rotas, monkeypatch):
    from app.config import settings

    usar_rotas(Rotas())
    monkeypatch.setattr(settings, "tool_calls_limit", 2)
    n = 0

    async def stream(_msgs: list[ModelMessage], _info: AgentInfo):
        nonlocal n
        n += 1
        yield {0: DeltaToolCall(name="web_search", json_args=json.dumps({"query": f"q{n}"}), tool_call_id=f"c{n}")}

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))

    uid, _h, _cid, r = await turno(client)

    assert r.status_code == 200
    assert '"type":"error"' in r.text.replace(" ", "")
    [ev] = await eventos("tool_limit_reached", user_id=uid)
    assert ev.payload["limite"] == 2
    assert n == 3


async def test_os_dois_modelos_esgotam_vira_502(client, usar_modelo, usar_reserva):
    primario, _ = falha_n_vezes(99, 503)
    reserva, _ = falha_n_vezes(99, 503, MODELO_RESERVA)
    usar_modelo(primario)
    usar_reserva(reserva)

    uid, h, cid, r = await turno(client)

    assert r.status_code == 502
    assert "503" in r.json()["detail"]
    [erro] = await eventos("llm_error", user_id=uid)
    assert erro.payload["tentativas"] == 6
    assert len(await eventos("llm_retry", user_id=uid)) == 4
    assert await eventos("llm_call", user_id=uid) == []
