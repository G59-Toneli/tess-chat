"""Roteador Jev (ticket 11). Resposta gravada do Jev, uma gravação só. Nada chama o Jev real."""

import json
from pathlib import Path

import httpx2
import pytest
from pydantic_ai.models.function import AgentInfo
from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy

from app.config import settings
from app.main import app
from app.roteador import apply_gate, cliente_jev, decidir, opcoes
from tests.test_anexos import PDF, parte, subir
from tests.test_auth import eventos
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_credito import linhas
from tests.test_conversas import criar, usuario
from tests.test_tools import Rotas, modelo_que_busca, usar_rotas  # noqa: F401  (fixture)

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "jev_golden.json").read_text(encoding="utf-8"))
CASOS = GOLDEN["casos"]
# ler_pdf não existe no registro: entra como Tool com a descrição do spike.
TOOLS_SPIKE = [("web_search", "-"), ("web_fetch", "-"), ("ler_pdf", GOLDEN["ler_pdf"])]


def jev_falso(responder) -> AsyncTypeSafeClient:
    return AsyncTypeSafeClient(api_key="teste", retry=RetryPolicy(max_retries=0), transport=httpx2.MockTransport(responder))


def gravada(caso: dict, vistos: list[dict] | None = None):
    """Devolve a resposta gravada do caso. Guarda o body de cada request que chegou ao Jev."""

    def responder(req: httpx2.Request) -> httpx2.Response:
        if vistos is not None:
            vistos.append(json.loads(req.content))
        return httpx2.Response(caso["status"], json=caso["response"])

    return responder


@pytest.fixture
def usar_jev():
    def trocar(responder):
        app.dependency_overrides[cliente_jev] = lambda: jev_falso(responder)

    yield trocar
    app.dependency_overrides.pop(cliente_jev, None)


# ---------- Golden set: os 10 casos do spike ----------


@pytest.mark.parametrize("caso", CASOS, ids=[c["esperado"] + ":" + c["texto"][:30] for c in CASOS])
async def test_golden_set_do_spike(caso):
    vistos: list[dict] = []
    d = await decidir(jev_falso(gravada(caso, vistos)), caso["texto"], caso["anexos"], opcoes(TOOLS_SPIKE))

    # O pedido de hoje é o mesmo que foi gravado: descrição, instrução e state não mudaram.
    assert vistos == [caso["request"]]
    escolha = apply_gate(d, settings.roteador_limiar)
    if caso["esperado"] == "ambiguo":
        assert d.confidence < settings.roteador_limiar
        assert escolha is None
    elif caso["esperado"] == "nenhuma":
        assert d.tool == "nenhuma"
        assert escolha is None
    else:
        assert d.tool == caso["esperado"]
        assert escolha == [caso["esperado"]]


def test_gate_usa_o_limiar_inclusivo():
    d = type("D", (), {"tool": "web_search", "confidence": 0.7})()
    assert apply_gate(d, 0.7) == ["web_search"]
    assert apply_gate(d, 0.71) is None
    assert apply_gate(None, 0.7) is None


# ---------- No chat ----------


def por_texto(texto: str) -> dict:
    return next(c for c in CASOS if c["texto"] == texto)


async def test_confianca_alta_forca_a_tool_so_no_primeiro_passo(client, usar_modelo, usar_rotas, usar_jev):
    caso = por_texto("Qual foi o resultado do jogo do Flamengo ontem?")
    pedidos: list[dict] = []
    usar_jev(gravada(caso, pedidos))
    usar_rotas(Rotas())
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_que_busca(vistos))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo(caso["texto"]), headers=h)
    assert r.status_code == 200, r.text

    # O Jev vê o texto do turno e só as Tools ativas mais `nenhuma`.
    [p] = pedidos
    assert p["state"] == {"mensagem_do_usuario": caso["texto"], "anexos_na_mensagem": "nenhum"}
    assert set(p["questions"]["tool"]["criteria"]) == {"web_search", "web_fetch", "nenhuma"}
    # Passo 1 forçado; passo 2 livre para responder em texto.
    assert [(i.model_settings or {}).get("tool_choice") for i in vistos] == [["web_search"], None]

    [ev] = await eventos("router_decision", user_id=uid)
    assert str(ev.conversation_id) == cid
    assert ev.payload["tool"] == "web_search"
    assert ev.payload["forcada"] is True
    assert ev.payload["distribution"] == caso["response"]["answers"]["tool"]["probabilities"]
    [jev] = await linhas(user_id=uid, model="jev-latest")
    # 452 tokens de entrada x US$ 0,042 por 1M = 18,98 µUSD, arredondado para cima.
    assert jev.cost_micro_usd == 19
    assert ev.cost_micro_usd == 19


async def test_caso_ambiguo_fica_auto(client, usar_modelo, usar_rotas, usar_jev):
    caso = por_texto("Resume esse PDF pra mim.")
    usar_jev(gravada(caso))
    usar_rotas(Rotas())
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_que_busca(vistos, chamar="nada"))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo(caso["texto"]), headers=h)
    assert r.status_code == 200, r.text
    assert [(i.model_settings or {}).get("tool_choice") for i in vistos] == [None]
    [ev] = await eventos("router_decision", user_id=uid)
    assert ev.payload["forcada"] is False
    assert ev.payload["confidence"] < settings.roteador_limiar


async def test_anexo_vai_no_state(client, usar_modelo, usar_rotas, usar_jev, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", tmp_path)
    caso = por_texto("Me faz um resumo desse contrato que eu te mandei.")
    pedidos: list[dict] = []
    usar_jev(gravada(caso, pedidos))
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([], chamar="nada"))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    # Anexo vai por referência (09b): sobe antes, manda a URL de /api/attachments.
    anexo = (await subir(client, h, "contrato.pdf", PDF, "application/pdf")).json()
    body = corpo(caso["texto"])
    body["messages"][-1]["parts"].append(parte(anexo))

    r = await client.post(f"/api/chat/{cid}", json=body, headers=h)
    assert r.status_code == 200, r.text
    assert pedidos[0]["state"]["anexos_na_mensagem"] == ["contrato.pdf"]


@pytest.mark.parametrize("status", [429, 529])
async def test_jev_indisponivel_cai_em_auto(client, usar_modelo, usar_rotas, usar_jev, status):
    usar_jev(lambda _req: httpx2.Response(status, json={"error": "indisponível"}))
    usar_rotas(Rotas())
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_que_busca(vistos))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("Quanto está o dólar hoje?"), headers=h)
    assert r.status_code == 200, r.text
    assert "Fonte:" in r.text  # o chat seguiu, o modelo decidiu sozinho
    assert (vistos[0].model_settings or {}).get("tool_choice") is None
    [ev] = await eventos("router_fallback", user_id=uid)
    assert ev.payload["status"] == status
    assert await eventos("router_decision", user_id=uid) == []
    assert await linhas(user_id=uid, model="jev-latest") == []


# ---------- Decisões expostas ao front ----------


async def test_decisoes_da_conversa_listam_tool_e_confianca(client, usar_modelo, usar_rotas, usar_jev):
    caso = por_texto("Qual foi o resultado do jogo do Flamengo ontem?")
    usar_jev(gravada(caso))
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([]))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    assert (await client.get(f"/api/conversations/{cid}/roteador", headers=h)).json() == []

    r = await client.post(f"/api/chat/{cid}", json=corpo(caso["texto"]), headers=h)
    assert r.status_code == 200, r.text

    r = await client.get(f"/api/conversations/{cid}/roteador", headers=h)
    assert r.status_code == 200
    [d] = r.json()
    assert d["tool"] == "web_search"
    assert d["confidence"] == caso["response"]["answers"]["tool"]["confidence"]
    assert d["forcada"] is True
    assert d["ts"]

    _, outro = await usuario(client)
    assert (await client.get(f"/api/conversations/{cid}/roteador", headers=outro)).status_code == 404
