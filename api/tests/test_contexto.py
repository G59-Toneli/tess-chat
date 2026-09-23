"""Indicador da janela de contexto (ticket 32). Turnos com FunctionModel que reporta input por palavra."""

from app.config import JANELAS_CONTEXTO, settings
from tests.test_chat import corpo
from tests.test_compactacao import LONGO, modelo_eco
from tests.test_conversas import criar, usuario

LITE = "gemini-3.1-flash-lite"


async def contexto(client, cid: str, h: dict) -> dict:
    r = await client.get(f"/api/conversations/{cid}/contexto", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def turno(client, cid: str, h: dict, texto: str) -> None:
    r = await client.post(f"/api/chat/{cid}", json=corpo(texto), headers=h)
    assert r.status_code == 200, r.text


async def ultimo_input(client, cid: str, h: dict) -> int:
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    return [m for m in msgs if m["role"] == "assistant"][-1]["input_tokens"]


async def test_conversa_nova_devolve_zero(client):
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    assert await contexto(client, cid, h) == {
        "usado": 0,
        "limite": JANELAS_CONTEXTO["gemini-3.8-flash"],
        "limiar_compactacao": settings.compactacao_limiar,
        "modelo": "gemini-3.8-flash",
    }


async def test_dois_turnos_usado_e_o_input_da_ultima_resposta(client, usar_modelo):
    usar_modelo(modelo_eco([]))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    await turno(client, cid, h, "primeira pergunta")
    depois_do_primeiro = (await contexto(client, cid, h))["usado"]
    await turno(client, cid, h, "segunda pergunta com mais palavras")
    usado = (await contexto(client, cid, h))["usado"]

    assert usado == await ultimo_input(client, cid, h)
    # O segundo turno carrega o primeiro no histórico: o uso cresce.
    assert usado > depois_do_primeiro > 0


async def test_limite_e_limiar_seguem_a_configuracao_da_conversa(client, monkeypatch):
    # Os três modelos têm a mesma janela na doc do Google. Um limite baixo no lite prova a troca.
    monkeypatch.setitem(JANELAS_CONTEXTO, LITE, 32_000)
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    r = await client.put(f"/api/conversations/{cid}/settings", json={"modelo": LITE, "compactacao_limiar": 20_000}, headers=h)
    assert r.status_code == 200, r.text

    ctx = await contexto(client, cid, h)
    assert (ctx["modelo"], ctx["limite"], ctx["limiar_compactacao"]) == (LITE, 32_000, 20_000)


async def test_uso_cai_depois_da_compactacao(client, usar_modelo, limiar, resumidor):
    usar_modelo(modelo_eco([]))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    usos = []
    for t in [f"um. {LONGO}", f"dois. {LONGO}", f"três. {LONGO}", "quatro?"]:
        await turno(client, cid, h, t)
        usos.append((await contexto(client, cid, h))["usado"])

    # O 4º turno troca o 1º pelo Resumo: carrega menos que o 3º.
    assert len(resumidor) == 1
    assert usos[3] < usos[2]


async def test_conversa_de_outro_usuario_responde_404(client):
    _, dono = await usuario(client)
    cid = (await criar(client, dono))["id"]
    _, outro = await usuario(client)
    r = await client.get(f"/api/conversations/{cid}/contexto", headers=outro)
    assert r.status_code == 404
