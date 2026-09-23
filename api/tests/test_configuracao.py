"""Configuração por Usuário e por Conversa (ticket 14). Modelos são FunctionModel."""

from typing import Annotated

from fastapi import Depends
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.chat import MODELO, modelo
from app.compactacao import MODELO_RESUMO
from app.config import settings
from app.configuracao import Configuracao, configuracao_do_turno
from app.conversas import Message
from app.credito import CreditLedger
from app.db import SessionLocal
from app.main import app
from tests.test_auditoria import demo
from tests.test_auth import eventos
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_compactacao import LONGO, modelo_eco, resumidor  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario
from tests.test_roteador import CASOS, gravada, usar_jev  # noqa: F401  (fixture)
from tests.test_tools import Rotas, modelo_que_busca, usar_rotas  # noqa: F401  (fixture)

LITE = "gemini-3.1-flash-lite"


async def put(client, url: str, h: dict, **campos):
    r = await client.put(url, json=campos, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def test_conversa_sobrepoe_usuario_que_sobrepoe_default(client):
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    outra = (await criar(client, h))["id"]

    padrao = (await client.get("/api/settings", headers=h)).json()["efetiva"]
    assert padrao == {
        "modelo": MODELO,
        "nivel_raciocinio": "low",
        "compactacao_limiar": settings.compactacao_limiar,
        "roteador_limiar": settings.roteador_limiar,
    }

    await put(client, "/api/settings", h, modelo=LITE, compactacao_limiar=5_000)
    conv = await put(client, f"/api/conversations/{cid}/settings", h, compactacao_limiar=3_000)
    assert conv["efetiva"] == {**padrao, "modelo": LITE, "compactacao_limiar": 3_000}
    # A outra Conversa só herda o Usuário.
    r = (await client.get(f"/api/conversations/{outra}/settings", headers=h)).json()
    assert r["efetiva"] == {**padrao, "modelo": LITE, "compactacao_limiar": 5_000}

    # null apaga o valor próprio e volta a herdar.
    conv = await put(client, f"/api/conversations/{cid}/settings", h, compactacao_limiar=None)
    assert conv["valores"]["compactacao_limiar"] is None
    assert conv["efetiva"]["compactacao_limiar"] == 5_000


async def test_settings_changed_leva_o_diff_e_nao_repete_sem_mudanca(client):
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    await put(client, "/api/settings", h, modelo=LITE)
    await put(client, "/api/settings", h, modelo=LITE)
    await put(client, f"/api/conversations/{cid}/settings", h, roteador_limiar=0.9, nivel_raciocinio="high")

    usuario_ev, conversa_ev = sorted(await eventos("settings_changed", user_id=uid), key=lambda e: e.id)
    assert usuario_ev.payload == {"escopo": "usuario", "alteracoes": {"modelo": {"de": None, "para": LITE}}}
    assert str(conversa_ev.conversation_id) == cid
    assert conversa_ev.payload == {
        "escopo": "conversa",
        "alteracoes": {"roteador_limiar": {"de": None, "para": 0.9}, "nivel_raciocinio": {"de": None, "para": "high"}},
    }


async def test_valores_invalidos_e_conversa_de_outro(client):
    _, h = await usuario(client)
    _, h2 = await usuario(client)
    cid = (await criar(client, h))["id"]

    for campos in ({"modelo": "gpt-9"}, {"roteador_limiar": 1.5}, {"compactacao_limiar": 0}, {"nivel_raciocinio": "max"}):
        assert (await client.put("/api/settings", json=campos, headers=h)).status_code == 422, campos
    assert (await client.get(f"/api/conversations/{cid}/settings", headers=h2)).status_code == 404
    assert (await client.put(f"/api/conversations/{cid}/settings", json={}, headers=h2)).status_code == 404
    assert (await client.get("/api/settings")).status_code == 401


async def test_baixar_o_limiar_dispara_a_compactacao_na_proxima_mensagem(client, usar_modelo, resumidor):
    usar_modelo(modelo_eco([]))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    for t in [f"um. {LONGO}", f"dois. {LONGO}", f"três. {LONGO}"]:
        assert (await client.post(f"/api/chat/{cid}", json=corpo(t), headers=h)).status_code == 200
    # Default de 100k: nada compactou.
    assert resumidor == []

    await put(client, f"/api/conversations/{cid}/settings", h, compactacao_limiar=2_000)
    assert (await client.post(f"/api/chat/{cid}", json=corpo("quatro"), headers=h)).status_code == 200

    assert len(resumidor) == 1
    [ev] = await eventos("compaction", user_id=uid)
    assert ev.payload["tokens_antes"] > 2_000
    assert ev.model == MODELO_RESUMO


async def test_flash_lite_fica_gravado_na_mensagem_e_no_ledger(client):
    vistos: list[AgentInfo] = []

    async def stream(_msgs: list[ModelMessage], info: AgentInfo):
        vistos.append(info)
        yield "oi"

    # Fábrica igual à real: o nome do modelo sai da Configuração do turno.
    def fabrica(cfg: Annotated[Configuracao, Depends(configuracao_do_turno)]):
        return FunctionModel(stream_function=stream, model_name=cfg.modelo)

    app.dependency_overrides[modelo] = fabrica
    try:
        uid, h = await usuario(client)
        cid = (await criar(client, h))["id"]
        await put(client, "/api/settings", h, modelo=LITE, nivel_raciocinio="high")

        r = await client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=h)
        assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.pop(modelo, None)

    async with SessionLocal() as s:
        msg = await s.scalar(select(Message).where(Message.conversation_id == cid, Message.role == "assistant"))
        ledger = (await s.scalars(select(CreditLedger.model).where(CreditLedger.user_id == uid))).all()
    assert msg.model == LITE
    assert ledger == [LITE]
    [ev] = await eventos("llm_call", user_id=uid)
    assert ev.model == LITE
    # O nível de raciocínio chega ao modelo.
    assert vistos[0].model_settings["google_thinking_config"] == {"thinking_level": "high"}


async def test_limiar_do_roteador_vem_da_configuracao(client, usar_modelo, usar_rotas, usar_jev):
    # web_fetch com confiança 0,99: o default 0,7 forçaria a Tool.
    caso = next(c for c in CASOS if c["response"]["answers"]["tool"]["confidence"] == 0.99)
    usar_jev(gravada(caso))
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([], chamar="nada"))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    await put(client, f"/api/conversations/{cid}/settings", h, roteador_limiar=1.0)

    assert (await client.post(f"/api/chat/{cid}", json=corpo(caso["texto"]), headers=h)).status_code == 200

    [ev] = await eventos("router_decision", user_id=uid)
    assert ev.payload["limiar"] == 1.0
    assert ev.payload["forcada"] is False


async def test_cap_por_usuario_so_admin(client):
    uid, h = await usuario(client)
    url = f"/api/admin/usuarios/{uid}/cap"
    assert (await client.put(url, json={"cap_micro_usd": 1}, headers=h)).status_code == 403

    hd = await demo(client)
    assert (await client.put(url, json={"cap_micro_usd": -1}, headers=hd)).status_code == 422
    r = await client.put(url, json={"cap_micro_usd": 500_000}, headers=hd)
    assert r.status_code == 200, r.text
    await put(client, url, hd, cap_micro_usd=700_000)

    assert (await client.get("/api/credits/me", headers=h)).json()["cap_micro_usd"] == 700_000
    evs = [e for e in sorted(await eventos("settings_changed"), key=lambda e: e.id) if e.payload.get("usuario_alvo") == str(uid)]
    assert [e.payload["alteracoes"] for e in evs] == [
        {"cap_micro_usd": {"de": settings.cap_usuario_micro_usd, "para": 500_000}},
        {"cap_micro_usd": {"de": 500_000, "para": 700_000}},
    ]
