"""Painel de auditoria e créditos (ticket 15)."""

from datetime import UTC, datetime

from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.auth import DEMO_EMAIL, garantir_admin, garantir_conta_demo
from app.chat import MODELO
from app.config import settings
from app.credito import Cap, CreditLedger, preco_vigente
from app.db import SessionLocal
from tests.test_auth import logar
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario
from tests.test_shares import compartilhar
from tests.test_tools import Rotas, modelo_que_busca, usar_rotas  # noqa: F401  (fixture)


async def demo(client) -> dict:
    """Conta demo promovida a admin por ADMIN_EMAIL, como o .env de produção faz com a conta do dono."""
    await garantir_conta_demo()
    antes, settings.admin_email = settings.admin_email, DEMO_EMAIL
    try:
        await garantir_admin()
    finally:
        settings.admin_email = antes
    token = (await logar(client, DEMO_EMAIL, settings.demo_password)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def auditoria(client, h, **params) -> dict:
    r = await client.get("/api/audit", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def test_fluxo_aparece_em_ordem(client, usar_modelo, usar_rotas):
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([]))
    uid, h = await usuario(client)  # registra e loga
    cid = (await criar(client, h))["id"]
    r = await client.post(f"/api/chat/{cid}", json=corpo("notícias de hoje"), headers=h)
    assert r.status_code == 200, r.text
    await compartilhar(client, h, cid)

    corpo_audit = await auditoria(client, h, limit=200)
    # A API devolve do mais recente para o mais antigo.
    tipos = [e["event_type"] for e in reversed(corpo_audit["items"])]
    esperado = ["login_ok", "conversation_created", "tool_call", "message_sent", "llm_call", "share_created"]
    assert [t for t in tipos if t in esperado] == esperado
    assert corpo_audit["total"] == len(corpo_audit["items"])
    assert {e["user_id"] for e in corpo_audit["items"]} == {str(uid)}
    [tool] = [e for e in corpo_audit["items"] if e["event_type"] == "tool_call"]
    assert tool["payload"]["tool"] == "web_search"
    assert tool["conversation_id"] == cid


async def test_filtros_e_paginacao(client, usar_modelo):
    async def stream(_m, _i: AgentInfo):
        yield "ok"

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))
    _, h = await usuario(client)
    c1 = (await criar(client, h))["id"]
    c2 = (await criar(client, h))["id"]
    for _ in range(3):
        assert (await client.post(f"/api/chat/{c1}", json=corpo("oi"), headers=h)).status_code == 200

    so_c1 = await auditoria(client, h, conversation_id=c1)
    assert {e["conversation_id"] for e in so_c1["items"]} == {c1}
    assert c2 not in {e["conversation_id"] for e in so_c1["items"]}

    llm = await auditoria(client, h, conversation_id=c1, event_type="llm_call")
    assert llm["total"] == 3
    assert {e["model"] for e in llm["items"]} == {MODELO}

    pag1 = await auditoria(client, h, conversation_id=c1, event_type="llm_call", limit=2, offset=0)
    pag2 = await auditoria(client, h, conversation_id=c1, event_type="llm_call", limit=2, offset=2)
    assert (len(pag1["items"]), len(pag2["items"]), pag2["total"]) == (2, 1, 3)
    ids = [e["id"] for e in pag1["items"] + pag2["items"]]
    assert ids == sorted(ids, reverse=True)

    ts = [e["ts"] for e in llm["items"]]
    antes = await auditoria(client, h, conversation_id=c1, event_type="llm_call", ate=min(ts))
    depois = await auditoria(client, h, conversation_id=c1, event_type="llm_call", desde=max(ts))
    assert antes["total"] >= 1 and depois["total"] >= 1
    assert all(e["ts"] <= min(ts) for e in antes["items"])

    tipos = (await client.get("/api/audit/tipos", headers=h)).json()
    assert {"login_ok", "conversation_created", "llm_call"} <= set(tipos)


async def test_usuario_comum_ve_so_o_proprio_e_demo_ve_tudo(client):
    ua, ha = await usuario(client)
    ub, hb = await usuario(client)
    ca = (await criar(client, ha))["id"]

    # B tenta ler A pelo filtro: recebe só os próprios eventos.
    visto_b = await auditoria(client, hb, user_id=str(ua), limit=200)
    assert {e["user_id"] for e in visto_b["items"]} == {str(ub)}
    assert (await auditoria(client, hb, conversation_id=ca))["items"] == []

    hd = await demo(client)
    me = (await client.get("/users/me", headers=hd)).json()
    assert me["is_superuser"] is True
    visto_demo = await auditoria(client, hd, user_id=str(ua))
    assert {e["event_type"] for e in visto_demo["items"]} >= {"login_ok", "conversation_created"}
    assert {e["user_id"] for e in visto_demo["items"]} == {str(ua)}
    tudo = await auditoria(client, hd, limit=200)
    assert tudo["total"] > visto_b["total"]


async def test_saldo_e_cap_menos_soma_do_ledger(client):
    uid, h = await usuario(client)
    async with SessionLocal() as s:
        preco = await preco_vigente(s, MODELO)
        s.add(Cap(user_id=uid, limite_micro_usd=1_000_000))
        for custo, modelo in ((1_234, MODELO), (5_000, MODELO), (766, "jev-latest")):
            s.add(
                CreditLedger(
                    user_id=uid, model=modelo, price_id=preco.id, input_tokens=10, output_tokens=5,
                    thinking_tokens=0, cache_read_tokens=0, cost_micro_usd=custo,
                )
            )
        await s.commit()
        soma = sum((await s.scalars(select(CreditLedger.cost_micro_usd).where(CreditLedger.user_id == uid))).all())

    r = await client.get("/api/credits/me/painel", params={"tz": "America/Sao_Paulo"}, headers=h)
    assert r.status_code == 200, r.text
    p = r.json()
    assert soma == 7_000
    assert p["saldo"] == {"gasto_micro_usd": 7_000, "cap_micro_usd": 1_000_000, "saldo_micro_usd": 993_000}
    assert {m["model"]: (m["custo_micro_usd"], m["chamadas"]) for m in p["por_modelo"]} == {
        MODELO: (6_234, 2),
        "jev-latest": (766, 1),
    }
    assert sum(d["custo_micro_usd"] for d in p["por_dia"]) == 7_000
    assert [lin["cost_micro_usd"] for lin in p["ultimas"]] == [766, 5_000, 1_234]


async def test_painel_global_e_admin_so_para_superuser(client):
    _, h = await usuario(client)
    assert (await client.get("/api/credits/global/painel", headers=h)).status_code == 403
    assert (await client.get("/api/admin/usuarios", headers=h)).status_code == 403
    assert (await client.get("/api/credits/me/painel", params={"tz": "Nao/Existe"}, headers=h)).status_code == 422

    hd = await demo(client)
    g = (await client.get("/api/credits/global/painel", headers=hd)).json()
    assert g["saldo"]["saldo_micro_usd"] == g["saldo"]["cap_micro_usd"] - g["saldo"]["gasto_micro_usd"]
    usuarios = (await client.get("/api/admin/usuarios", headers=hd)).json()
    assert DEMO_EMAIL in {u["email"] for u in usuarios}
    assert sum(u["gasto_micro_usd"] for u in usuarios) == g["saldo"]["gasto_micro_usd"]


async def test_painel_exige_login(client):
    for rota in ("/api/audit", "/api/audit/tipos", "/api/credits/me/painel", "/api/admin/usuarios"):
        assert (await client.get(rota)).status_code == 401, rota



async def test_gasto_por_dia_usa_o_fuso_do_browser(client):
    uid, h = await usuario(client)
    async with SessionLocal() as s:
        preco = await preco_vigente(s, MODELO)
        # 01:30 UTC do dia 23 = 22:30 do dia 22 em São Paulo.
        s.add(
            CreditLedger(
                ts=datetime(2026, 9, 23, 1, 30, tzinfo=UTC), user_id=uid, model=MODELO, price_id=preco.id,
                input_tokens=1, output_tokens=1, thinking_tokens=0, cache_read_tokens=0, cost_micro_usd=42,
            )
        )
        await s.commit()

    async def dias(tz: str) -> list[dict]:
        return (await client.get("/api/credits/me/painel", params={"tz": tz}, headers=h)).json()["por_dia"]

    assert await dias("America/Sao_Paulo") == [{"dia": "2026-09-22", "custo_micro_usd": 42}]
    assert await dias("UTC") == [{"dia": "2026-09-23", "custo_micro_usd": 42}]


async def test_demo_ve_o_proprio_gasto_depois_de_um_turno(client, usar_modelo, usar_rotas):
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([]))
    hd = await demo(client)
    antes = (await client.get("/api/credits/me/painel", headers=hd)).json()["saldo"]["gasto_micro_usd"]
    cid = (await criar(client, hd, "Notícias do dia"))["id"]

    assert (await client.post(f"/api/chat/{cid}", json=corpo("notícias de hoje"), headers=hd)).status_code == 200

    p = (await client.get("/api/credits/me/painel", headers=hd)).json()
    assert p["ultimas"][0]["conversation_id"] == cid
    assert p["saldo"]["gasto_micro_usd"] == antes + p["ultimas"][0]["cost_micro_usd"]
    assert p["saldo"]["gasto_micro_usd"] > antes
