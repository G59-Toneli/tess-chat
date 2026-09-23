"""Tools nativas com toggle por Conversa (ticket 10). HTTP das tools é resposta gravada."""

import json
import re
from pathlib import Path

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

from app.chat import MODELO
from app.main import app
from app.tools import transporte, web_fetch
from tests.test_auth import eventos
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario

FIX = Path(__file__).parent / "fixtures"
TAVILY = json.loads((FIX / "tavily_search.json").read_text(encoding="utf-8"))
JINA = (FIX / "jina_example.md").read_text(encoding="utf-8")
HTML = (FIX / "pagina.html").read_text(encoding="utf-8")


class Rotas(httpx.MockTransport):
    """Tavily, Jina e um site qualquer, com resposta gravada. Guarda os requests vistos."""

    def __init__(self, jina_status: int = 200):
        self.vistas: list[httpx.Request] = []
        super().__init__(self._responder)
        self.jina_status = jina_status

    def _responder(self, req: httpx.Request) -> httpx.Response:
        self.vistas.append(req)
        if req.url.host == "api.tavily.com":
            return httpx.Response(200, json=TAVILY)
        if req.url.host == "r.jina.ai":
            ok = self.jina_status == 200
            return httpx.Response(self.jina_status, text=JINA if ok else "erro")
        return httpx.Response(200, text=HTML, headers={"content-type": "text/html; charset=utf-8"})


@pytest.fixture
def usar_rotas():
    def trocar(t):
        app.dependency_overrides[transporte] = lambda: t
        return t

    yield trocar
    app.dependency_overrides.pop(transporte, None)


def retornos(msgs: list[ModelMessage]) -> list[ToolReturnPart]:
    return [p for m in msgs if isinstance(m, ModelRequest) for p in m.parts if isinstance(p, ToolReturnPart)]


def modelo_que_busca(vistos: list[AgentInfo], chamar: str = "web_search"):
    """Chama a tool no 1º request, se ela estiver disponível. No 2º cita a URL que a tool devolveu."""

    async def stream(msgs: list[ModelMessage], info: AgentInfo):
        vistos.append(info)
        feitos = retornos(msgs[-1:])
        if not feitos and chamar in [t.name for t in info.function_tools]:
            args = {"query": "notícias de hoje"} if chamar == "web_search" else {"url": "https://example.com"}
            yield {0: DeltaToolCall(name=chamar, json_args=json.dumps(args), tool_call_id="c1")}
            return
        urls = re.findall(r"https?://[^\s\"')\]]+", str(feitos[-1].content)) if feitos else []
        yield f"Resposta. Fonte: {urls[0]}" if urls else "Sem tool, sem fonte."

    return FunctionModel(stream_function=stream, model_name=MODELO)


async def ligar(client, h, cid, **mudancas) -> list[dict]:
    r = await client.put(f"/api/conversations/{cid}/tools", json=mudancas, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def estado(lista: list[dict]) -> dict[str, bool]:
    return {t["nome"]: t["ativa"] for t in lista}


async def test_catalogo_lista_as_nativas(client):
    _, h = await usuario(client)
    r = await client.get("/api/tools", headers=h)
    assert r.status_code == 200
    por_nome = {t["nome"]: t for t in r.json()}
    assert {"web_search", "web_fetch"} <= set(por_nome)
    assert por_nome["web_search"]["origem"] == "nativa"
    assert por_nome["web_fetch"]["schema"]["required"] == ["url"]
    assert (await client.get("/api/tools")).status_code == 401


async def test_catalogo_devolve_descricao_para_o_usuario(client):
    """Tela mostra descricao_usuario, sem instrução ao modelo. O modelo segue com descricao."""
    _, h = await usuario(client)
    por_nome = {t["nome"]: t for t in (await client.get("/api/tools", headers=h)).json()}

    envio = por_nome["gmail_send"]
    assert envio["descricao_usuario"]
    assert "usuário" not in envio["descricao_usuario"] and "NÃO" not in envio["descricao_usuario"]
    assert "NÃO envia" in envio["descricao"]
    assert all(t["descricao_usuario"] for t in por_nome.values())
    cid = (await criar(client, h))["id"]
    na_conversa = {t["nome"]: t for t in (await client.get(f"/api/conversations/{cid}/tools", headers=h)).json()}
    assert na_conversa["web_search"]["descricao_usuario"] == por_nome["web_search"]["descricao_usuario"]


async def test_toggle_por_conversa_e_auditado(client):
    uid, h = await usuario(client)
    c1 = (await criar(client, h))["id"]
    c2 = (await criar(client, h))["id"]

    devolvido = await ligar(client, h, c1, web_search=False)

    r1 = (await client.get(f"/api/conversations/{c1}/tools", headers=h)).json()
    r2 = (await client.get(f"/api/conversations/{c2}/tools", headers=h)).json()
    assert estado(devolvido) == estado(r1)
    assert estado(r1)["web_search"] is False
    assert estado(r2)["web_search"] is True  # padrão: herda ativa_global
    [ev] = await eventos("tool_toggled", user_id=uid)
    assert str(ev.conversation_id) == c1
    assert ev.payload == {"web_search": False}

    await ligar(client, h, c1, web_search=True)
    r1 = (await client.get(f"/api/conversations/{c1}/tools", headers=h)).json()
    assert estado(r1)["web_search"] is True


async def test_toggle_de_conversa_alheia_e_tool_inexistente(client):
    _, ha = await usuario(client)
    _, hb = await usuario(client)
    cid = (await criar(client, ha))["id"]
    url = f"/api/conversations/{cid}/tools"

    assert (await client.get(url, headers=hb)).status_code == 404
    assert (await client.put(url, json={"web_search": False}, headers=hb)).status_code == 404
    assert (await client.put(url, json={"nao_existe": True}, headers=ha)).status_code == 422


async def test_web_search_desligada_nao_gera_tool_call(client, usar_modelo, usar_rotas):
    t = usar_rotas(Rotas())
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_que_busca(vistos))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    await ligar(client, h, cid, web_search=False, web_fetch=False)

    r = await client.post(f"/api/chat/{cid}", json=corpo("notícias de hoje"), headers=h)

    assert r.status_code == 200, r.text
    assert [i.function_tools for i in vistos] == [[]]
    assert await eventos("tool_call", user_id=uid) == []
    assert t.vistas == []


async def test_web_search_ligada_gera_tool_call_e_cita_fonte(client, usar_modelo, usar_rotas):
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([]))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("notícias de hoje"), headers=h)

    assert r.status_code == 200, r.text
    [ev] = await eventos("tool_call", user_id=uid)
    assert str(ev.conversation_id) == cid
    assert ev.payload["tool"] == "web_search"
    assert ev.payload["args"] == {"query": "notícias de hoje"}
    assert ev.payload["result_chars"] > 0
    assert ev.latency_ms is not None and ev.latency_ms >= 0
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert TAVILY["results"][0]["url"] in msgs[-1]["parts"][-1]["text"]


async def test_historico_com_tool_volta_ao_modelo(client, usar_modelo, usar_rotas):
    usar_rotas(Rotas())
    vistas: list[list[ModelMessage]] = []
    base = modelo_que_busca([])

    async def stream(msgs, info):
        vistas.append(msgs)
        async for x in base.stream_function(msgs, info):
            yield x

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    assert (await client.post(f"/api/chat/{cid}", json=corpo("notícias de hoje"), headers=h)).status_code == 200
    r2 = await client.post(f"/api/chat/{cid}", json=corpo("e agora?"), headers=h)

    assert r2.status_code == 200, r2.text
    # O 2º turno recebe do banco a chamada e o retorno da tool do 1º.
    fonte = TAVILY["results"][0]["url"]
    assert any(fonte in str(p.content) for p in retornos(vistas[-1]))


async def test_web_fetch_devolve_texto_do_jina():
    texto = await web_fetch("https://example.com", Rotas())
    assert "Example Domain" in texto
    assert "<" not in texto


async def test_web_fetch_cai_no_trafilatura_quando_jina_falha():
    t = Rotas(jina_status=503)
    texto = await web_fetch("https://site.test/pao", t)
    assert "Sove a massa por dez minutos" in texto
    assert "<p>" not in texto and "rastreio" not in texto and "Início" not in texto
    assert [r.url.host for r in t.vistas] == ["r.jina.ai", "site.test"]


async def test_web_fetch_ligada_no_chat_gera_tool_call(client, usar_modelo, usar_rotas):
    usar_rotas(Rotas())
    usar_modelo(modelo_que_busca([], chamar="web_fetch"))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("leia example.com"), headers=h)

    assert r.status_code == 200, r.text
    [ev] = await eventos("tool_call", user_id=uid)
    assert ev.payload["tool"] == "web_fetch"
    assert ev.payload["args"] == {"url": "https://example.com"}


async def test_toggle_global_desliga_em_toda_conversa_e_e_auditado(client):
    from tests.test_auditoria import demo

    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    hd = await demo(client)
    uid = (await client.get("/users/me", headers=hd)).json()["id"]
    try:
        # Toggle global é só do admin (ticket 14).
        assert (await client.put("/api/tools/web_fetch", json={"ativa_global": False}, headers=h)).status_code == 403
        r = await client.put("/api/tools/web_fetch", json={"ativa_global": False}, headers=hd)
        assert r.status_code == 200, r.text
        assert r.json()["ativa_global"] is False
        catalogo = {t["nome"]: t for t in (await client.get("/api/tools", headers=h)).json()}
        assert catalogo["web_fetch"]["ativa_global"] is False
        # Conversa sem toggle próprio herda o global.
        conv = (await client.get(f"/api/conversations/{cid}/tools", headers=h)).json()
        assert estado(conv)["web_fetch"] is False
        ev = max(await eventos("tool_toggled_global", user_id=uid), key=lambda e: e.id)
        assert ev.payload == {"tool": "web_fetch", "ativa_global": False}
    finally:
        await client.put("/api/tools/web_fetch", json={"ativa_global": True}, headers=hd)


async def test_toggle_global_de_tool_inexistente_e_sem_login(client):
    from tests.test_auditoria import demo

    h = await demo(client)
    assert (await client.put("/api/tools/nao_existe", json={"ativa_global": True}, headers=h)).status_code == 404
    assert (await client.put("/api/tools/web_fetch", json={"ativa_global": True})).status_code == 401


# ---------- Teto de texto com aviso de corte (ticket 31) ----------


async def test_web_fetch_acima_do_teto_vem_com_a_frase_de_corte():
    from app.tools import LIMITE_CHARS

    grande = httpx.MockTransport(lambda _req: httpx.Response(200, text="a" * (LIMITE_CHARS + 5000)))
    texto = await web_fetch("https://example.com", grande)

    assert texto.startswith("a" * LIMITE_CHARS)
    assert texto.endswith(f"[resultado cortado em {LIMITE_CHARS} caracteres; peça só o trecho necessário]")


async def test_resultado_mcp_acima_do_teto_chega_ao_modelo_com_a_frase_de_corte(client):
    import uuid

    from pydantic_ai import Agent, FunctionToolset

    from app.tools import LIMITE_CHARS_MCP, Auditada

    uid, _ = await usuario(client)
    ts = FunctionToolset()

    @ts.tool_plain
    def schema_grande() -> str:
        return "x" * (LIMITE_CHARS_MCP + 1000)

    vistas: list[list[ModelMessage]] = []

    async def stream(msgs: list[ModelMessage], _info: AgentInfo):
        vistas.append(msgs)
        if len(vistas) == 1:
            yield {0: DeltaToolCall(name="schema_grande", json_args="{}", tool_call_id="c1")}
            return
        yield "ok"

    toolset = Auditada(ts, uid, uuid.uuid4(), {"schema_grande": "mcp"})
    async with Agent(FunctionModel(stream_function=stream), toolsets=[toolset]).run_stream("oi") as r:
        await r.get_output()

    [ret] = retornos(vistas[-1])
    assert ret.content.startswith("x" * LIMITE_CHARS_MCP)
    assert ret.content.endswith(f"[resultado cortado em {LIMITE_CHARS_MCP} caracteres; peça só o trecho necessário]")
