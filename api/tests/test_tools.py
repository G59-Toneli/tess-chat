"""Tools nativas com toggle por Conversa (ticket 10). HTTP das tools é resposta gravada."""

import json
import re
from pathlib import Path

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

from app.chat import MODELO
from app.tools import schema_para_modelo, web_fetch
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_conectores import conectar
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


# DNS falso: nenhum teste depende de rede. `postgres` é o nome do banco na rede do compose.
DNS = {"postgres": "172.18.0.2", "interno.test": "10.0.0.5"}


@pytest.fixture(autouse=True)
def dns_falso(monkeypatch):
    from app import rede

    async def resolver(host: str, _porta: int) -> list[str]:
        return [DNS.get(host, "93.184.216.34")]

    monkeypatch.setattr(rede, "resolver_ips", resolver)


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


async def test_catalogo_devolve_descricao_para_o_usuario(client, google):
    """Tela mostra descricao_usuario, sem instrução ao modelo. O modelo segue com descricao."""
    _, h = await usuario(client)
    await conectar(client, h)
    por_nome = {t["nome"]: t for t in (await client.get("/api/tools", headers=h)).json()}

    envio = por_nome["gmail_send"]
    assert envio["descricao_usuario"]
    assert "usuário" not in envio["descricao_usuario"] and "NÃO" not in envio["descricao_usuario"]
    assert "NÃO envia" in envio["descricao"]
    assert all(t["descricao_usuario"] for t in por_nome.values())
    cid = (await criar(client, h))["id"]
    na_conversa = {t["nome"]: t for t in (await client.get(f"/api/conversations/{cid}/tools", headers=h)).json()}
    assert na_conversa["web_search"]["descricao_usuario"] == por_nome["web_search"]["descricao_usuario"]


async def test_catalogo_descreve_pdf_e_recentes_do_drive(client, google):
    """A tela vê o que drive_search_read faz desde os tickets 38 e 39 (ticket 42)."""
    _, h = await usuario(client)
    await conectar(client, h)
    por_nome = {t["nome"]: t for t in (await client.get("/api/tools", headers=h)).json()}

    drive = por_nome["drive_search_read"]["descricao_usuario"]
    assert "PDF" in drive and "recentes" in drive


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


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "http://postgres:5432/", "file:///etc/passwd"]
)
async def test_web_fetch_recusa_endereco_interno_sem_request(url):
    t = Rotas()
    texto = await web_fetch(url, t)
    assert texto.startswith("web_fetch recusado")
    assert t.vistas == []


async def test_web_fetch_recusa_redirect_de_url_publica_para_ip_interno():
    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.host == "r.jina.ai":
            return httpx.Response(503)
        if req.url.host == "publico.test":
            return httpx.Response(302, headers={"location": "http://interno.test/admin"})
        return httpx.Response(200, text="segredo interno")

    vistas: list[str] = []
    t = httpx.MockTransport(lambda req: vistas.append(req.url.host) or responder(req))
    texto = await web_fetch("https://publico.test/x", t)

    assert texto.startswith("web_fetch recusado") and "10.0.0.5" in texto
    assert vistas == ["r.jina.ai", "publico.test"]


async def test_web_fetch_segue_redirect_entre_urls_publicas():
    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.host == "r.jina.ai":
            return httpx.Response(503)
        if req.url.path == "/velho":
            return httpx.Response(301, headers={"location": "/pao"})
        return httpx.Response(200, text=HTML, headers={"content-type": "text/html; charset=utf-8"})

    texto = await web_fetch("https://site.test/velho", httpx.MockTransport(responder))
    assert "Sove a massa por dez minutos" in texto


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
    def schema_grande() -> dict:
        return {"campos": "x" * (LIMITE_CHARS_MCP + 1000), "obrigatorio": True}

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
    assert ret.content.startswith('{"campos": "xxx')  # JSON, não repr do dict
    assert ret.content.endswith(f"[resultado cortado em {LIMITE_CHARS_MCP} caracteres; peça só o trecho necessário]")


# ---------- Args de tool MCP e validação (ticket 33) ----------


def test_string_json_aninhada_vira_objeto_e_string_comum_fica():
    from app.tools import desembrulhar_json

    # Formato exato que o Gemini mandou ao Stripe no turno real do ticket 31.
    args = {
        "stripe_api_operation_id": "PostPaymentLinks",
        "parameters": {"line_items": [{"quantity": 1, "price_data": '{ "currency": "brl", "unit_amount": 100000 }'}]},
        "texto": "Olá {mundo}",
        "chaves": "{mundo}",
        "lista": "[1, 2]",
    }

    saida = desembrulhar_json(args)

    assert saida["parameters"]["line_items"][0]["price_data"] == {"currency": "brl", "unit_amount": 100000}
    assert saida["texto"] == "Olá {mundo}" and saida["chaves"] == "{mundo}"
    assert saida["lista"] == [1, 2]
    assert saida["stripe_api_operation_id"] == "PostPaymentLinks"


async def test_args_invalidos_duas_vezes_encerram_o_turno_com_aviso(client, usar_modelo):
    from tests.test_resiliencia import chunks

    uid, h = await usuario(client)

    async def stream(msgs: list[ModelMessage], _info: AgentInfo):
        n = sum(1 for m in msgs if isinstance(m, ModelRequest))
        # Sem o campo query: a validação do Pydantic recusa.
        yield {0: DeltaToolCall(name="web_search", json_args="{}", tool_call_id=f"c{n}")}

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("busca algo"), headers=h)

    assert r.status_code == 200, r.text
    assert "error" not in [c["type"] for c in chunks(r.text)]
    [aviso] = [c for c in chunks(r.text) if c["type"] == "data-turno-interrompido"]
    assert aviso["data"]["motivo"] == "tool_falhou" and aviso["data"]["tool"] == "web_search"
    assert "query" in aviso["data"]["texto"]
    falhas = await eventos("tool_call", user_id=uid)
    assert len(falhas) == 2 and all("erro" in f.payload for f in falhas)


# ---------- Schema aberto de tool MCP vira string JSON (ticket 35) ----------

# Trecho real de stripe_api_write (servidor Stripe MCP, 23/09).
STRIPE_WRITE = {
    "type": "object",
    "required": ["stripe_api_operation_id", "parameters"],
    "properties": {
        "stripe_api_operation_id": {"type": "string", "description": "Operation id."},
        "parameters": {"type": "object", "description": "Parameters for the API call."},
        "human_confirmation": {
            "type": "object",
            "properties": {"approval_token": {"type": "string", "description": "Approval token."}},
            "description": "Confirmação humana.",
        },
        "itens": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
    },
}


def test_objeto_livre_vira_string_json_e_objeto_com_properties_fica():
    novo = schema_para_modelo(STRIPE_WRITE)

    props = novo["properties"]
    assert props["parameters"] == {
        "type": "string",
        "description": "Parameters for the API call. — JSON serializado do objeto",
    }
    assert props["itens"]["type"] == "string"
    assert props["human_confirmation"] == STRIPE_WRITE["properties"]["human_confirmation"]
    assert props["stripe_api_operation_id"] == STRIPE_WRITE["properties"]["stripe_api_operation_id"]
    assert novo["required"] == STRIPE_WRITE["required"]
    assert STRIPE_WRITE["properties"]["parameters"]["type"] == "object"  # o registro não muda
