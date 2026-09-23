"""Crédito: Tabela de Preço, Ledger, reserva/acerto, Cap (ticket 08)."""

import math
import uuid
from fractions import Fraction

from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RunUsage
from sqlalchemy import func, select, text

from app.chat import MODELO
from app.credito import Cap, CreditLedger, PrecoModelo, debit
from app.db import SessionLocal
from tests.test_auth import eventos
from tests.test_chat import GRAVADA, _nunca, corpo, gemini_falso, usage_gravado, usar_modelo  # noqa: F401
from tests.test_conversas import criar, usuario


async def linhas(**filtro) -> list[CreditLedger]:
    async with SessionLocal() as s:
        q = select(CreditLedger).order_by(CreditLedger.id)
        for campo, valor in filtro.items():
            q = q.where(getattr(CreditLedger, campo) == valor)
        return list((await s.scalars(q)).all())


async def test_soma_do_ledger_bate_com_usage_gravado(client, usar_modelo):
    usar_modelo(gemini_falso(200, GRAVADA.read_bytes(), "text/event-stream"))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    for texto in ("primeira", "segunda"):
        r = await client.post(f"/api/chat/{cid}", json=corpo(texto), headers=h)
        assert r.status_code == 200, r.text

    # Preço do ADR 0003 em USD por 1M. Input sem cache, cache à parte, output já inclui thinking.
    um = usage_gravado()
    cache = um.get("cachedContentTokenCount", 0)
    usd = (
        (um["promptTokenCount"] - cache) * Fraction("0.75")
        + cache * Fraction("0.075")
        + (um["candidatesTokenCount"] + um.get("thoughtsTokenCount", 0)) * Fraction("3.75")
    )
    por_chamada = math.ceil(usd)  # USD/1M × tokens = micro-USD

    rows = await linhas(conversation_id=uuid.UUID(cid))
    assert len(rows) == 2
    assert all(r.model == MODELO for r in rows)
    assert sum(r.cost_micro_usd for r in rows) == 2 * por_chamada

    me = (await client.get("/api/credits/me", headers=h)).json()
    assert me["gasto_micro_usd"] == 2 * por_chamada
    assert me["saldo_micro_usd"] == me["cap_micro_usd"] - 2 * por_chamada
    glob = (await client.get("/api/credits/global", headers=h)).json()
    assert glob["gasto_micro_usd"] >= 2 * por_chamada


async def test_cap_de_1_micro_usd_recusa_antes_do_provedor(client, usar_modelo):
    usar_modelo(FunctionModel(stream_function=lambda _m, _i: _nunca(), model_name=MODELO))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    async with SessionLocal() as s:
        s.add(Cap(user_id=uid, limite_micro_usd=1))
        await s.commit()

    r = await client.post(f"/api/chat/{cid}", json=corpo("oi"), headers=h)

    assert r.status_code == 402, r.text
    [ev] = await eventos("cap_reached", user_id=uid)
    assert ev.payload["escopo"] == "usuario"
    assert ev.payload["cap"] == 1
    assert await linhas(user_id=uid) == []
    assert (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json() == []


async def test_nova_vigencia_nao_altera_linhas_antigas(client, usar_modelo):
    nome = f"modelo-teste-{uuid.uuid4().hex[:8]}"

    async def stream(_m, _i):
        yield "ok"

    usar_modelo(FunctionModel(stream_function=stream, model_name=nome))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    async def novo_preco(entrada: int, saida: int, desde: str) -> int:
        async with SessionLocal() as s:
            p = PrecoModelo(
                model=nome,
                input_micro_usd_1m=entrada,
                output_micro_usd_1m=saida,
                cache_micro_usd_1m=0,
                thinking_micro_usd_1m=saida,
                vigente_desde=text(desde),
            )
            s.add(p)
            await s.commit()
            return p.id

    antigo = await novo_preco(10_000_000, 20_000_000, "now() - interval '1 day'")
    assert (await client.post(f"/api/chat/{cid}", json=corpo("um"), headers=h)).status_code == 200
    [primeira] = await linhas(user_id=uid)

    novo = await novo_preco(30_000_000, 60_000_000, "now()")
    assert (await client.post(f"/api/chat/{cid}", json=corpo("dois"), headers=h)).status_code == 200

    velha, nova = await linhas(user_id=uid)
    assert (velha.id, velha.price_id, velha.cost_micro_usd) == (primeira.id, antigo, primeira.cost_micro_usd)
    assert nova.price_id == novo
    # Preço 3x mais caro: o custo por token subiu.
    tokens = lambda r: r.input_tokens + r.output_tokens  # noqa: E731
    assert nova.cost_micro_usd * tokens(velha) > velha.cost_micro_usd * tokens(nova)


def test_debit_cobra_input_sem_cache_cache_e_output_com_thinking():
    preco = PrecoModelo(
        input_micro_usd_1m=1_000_000,  # 1 micro-USD por token
        output_micro_usd_1m=10_000_000,
        cache_micro_usd_1m=100_000,
        thinking_micro_usd_1m=20_000_000,
    )
    uso = RunUsage(input_tokens=1000, cache_read_tokens=400, output_tokens=50, details={"thoughts_tokens": 20})
    # 600 × 1 + 400 × 0,1 + 30 × 10 + 20 × 20 = 600 + 40 + 300 + 400
    assert debit(uso, preco) == 1340


def test_debit_arredonda_para_cima():
    preco = PrecoModelo(
        input_micro_usd_1m=750_000, output_micro_usd_1m=0, cache_micro_usd_1m=0, thinking_micro_usd_1m=0
    )
    assert debit(RunUsage(input_tokens=1), preco) == 1
    assert debit(RunUsage(), preco) == 0


async def test_rota_de_credito_exige_login(client):
    assert (await client.get("/api/credits/me")).status_code == 401
    assert (await client.get("/api/credits/global")).status_code == 401


async def test_ledger_somente_insercao():
    async with SessionLocal() as s:
        assert (await s.scalar(select(func.count()).select_from(CreditLedger))) is not None
        try:
            await s.execute(text("UPDATE credit_ledger SET cost_micro_usd = 0"))
        except Exception as e:  # noqa: BLE001
            assert "permission denied" in str(e)
        else:
            raise AssertionError("tess_app não devia poder alterar o Ledger")
