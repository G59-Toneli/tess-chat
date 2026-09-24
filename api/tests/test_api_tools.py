"""Tool por API (ticket 59). HTTP da API cadastrada é MockTransport; nenhum teste sai para a rede."""

import json
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.db import SessionLocal
from app.tools import Tool
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_conectores import modelo_que_chama, ultima_resposta
from tests.test_conversas import criar, usuario

SEGREDO = "chave-secreta-123"
DNS = {"interno.test": "10.0.0.5"}


@pytest.fixture(autouse=True)
def dns_falso(monkeypatch):
    from app import rede

    async def resolver(host: str, _porta: int) -> list[str]:
        return [DNS.get(host, "93.184.216.34")]

    monkeypatch.setattr(rede, "resolver_ips", resolver)


class Api(httpx.MockTransport):
    """API falsa. `responder` decide a resposta; guarda os requests vistos."""

    def __init__(self, responder=None):
        self.vistas: list[httpx.Request] = []
        self.responder = responder or (lambda _req: httpx.Response(200, json={"cep": "01001-000", "uf": "SP"}))
        super().__init__(self._responder)

    def _responder(self, req: httpx.Request) -> httpx.Response:
        self.vistas.append(req)
        return self.responder(req)


@pytest.fixture
def api(usar_rotas):
    return usar_rotas(Api())


def viacep(**mudancas) -> dict:
    d = {
        "nome": "cep",
        "descricao": "Consulta endereço pelo CEP.",
        "metodo": "GET",
        "url": "https://viacep.test/ws/{cep}/json/",
        "parametros": [{"nome": "cep", "tipo": "string", "descricao": "CEP com 8 dígitos", "obrigatorio": True}],
        "exemplo": {"cep": "01001000"},
    }
    return {**d, **mudancas}


async def cadastrar(client, h, body: dict):
    return await client.post("/api/api-tools", json=body, headers=h)


async def contagens(uid: uuid.UUID) -> tuple[int, int]:
    async with SessionLocal() as s:
        linhas = await s.scalar(text("SELECT count(*) FROM api_tools WHERE user_id = :u"), {"u": uid})
        tools = await s.scalar(
            text("SELECT count(*) FROM tools t JOIN api_tools a ON a.id = t.api_tool_id WHERE a.user_id = :u"), {"u": uid}
        )
    return linhas, tools


# ---------- Cadastro ----------


async def test_cadastro_com_exemplo_2xx_grava_linha_e_tool_com_schema(client, api):
    uid, h = await usuario(client)
    params = [
        {"nome": "cep", "tipo": "string", "descricao": "CEP", "obrigatorio": True},
        {"nome": "limite", "tipo": "integer", "descricao": "Máximo de itens", "obrigatorio": False},
    ]

    r = await cadastrar(client, h, viacep(parametros=params))

    assert r.status_code == 201, r.text
    out = r.json()
    assert out["tool_nome"].startswith("api_") and out["tool_nome"].endswith("_cep")
    assert [str(req.url) for req in api.vistas] == ["https://viacep.test/ws/01001000/json/"]
    async with SessionLocal() as s:
        tool = await s.get(Tool, out["tool_nome"])
    assert tool.origem == "api" and tool.descricao == "Consulta endereço pelo CEP."
    assert tool.schema == {
        "type": "object",
        "properties": {
            "cep": {"type": "string", "description": "CEP"},
            "limite": {"type": "integer", "description": "Máximo de itens"},
        },
        "required": ["cep"],
    }
    lista = (await client.get("/api/api-tools", headers=h)).json()
    assert [t["id"] for t in lista] == [out["id"]]
    [ev] = await eventos("api_tool_added", user_id=uid)
    assert ev.payload["tool"] == out["tool_nome"]


async def test_exemplo_404_da_502_e_nao_grava(client, usar_rotas):
    usar_rotas(Api(lambda _req: httpx.Response(404, text="CEP não encontrado")))
    uid, h = await usuario(client)

    r = await cadastrar(client, h, viacep())

    assert r.status_code == 502
    assert "404" in r.json()["detail"] and "CEP não encontrado" in r.json()["detail"]
    assert await contagens(uid) == (0, 0)


async def test_exemplo_com_timeout_da_502_e_nao_grava(client, usar_rotas):
    def lento(req):
        raise httpx.ReadTimeout("lento", request=req)

    usar_rotas(Api(lento))
    uid, h = await usuario(client)

    r = await cadastrar(client, h, viacep())

    assert r.status_code == 502 and "15 s" in r.json()["detail"]
    assert await contagens(uid) == (0, 0)


async def test_placeholder_sem_parametro_da_422(client, api):
    uid, h = await usuario(client)
    r = await cadastrar(client, h, viacep(url="https://viacep.test/ws/{cep}/{formato}/"))
    assert r.status_code == 422 and "formato" in r.json()["detail"]
    assert api.vistas == [] and await contagens(uid) == (0, 0)


async def test_parametro_obrigatorio_nao_usado_da_422(client, api):
    _, h = await usuario(client)
    params = [
        {"nome": "cep", "tipo": "string", "descricao": "", "obrigatorio": True},
        {"nome": "sobra", "tipo": "string", "descricao": "", "obrigatorio": True},
    ]
    r = await cadastrar(client, h, viacep(parametros=params, exemplo={"cep": "1", "sobra": "x"}))
    assert r.status_code == 422 and "sobra" in r.json()["detail"]
    assert api.vistas == []


async def test_parametro_opcional_nao_usado_vira_query(client, api):
    _, h = await usuario(client)
    params = [
        {"nome": "cep", "tipo": "string", "descricao": "", "obrigatorio": True},
        {"nome": "campos", "tipo": "string", "descricao": "", "obrigatorio": False},
    ]
    r = await cadastrar(client, h, viacep(parametros=params, exemplo={"cep": "1", "campos": "uf,cep"}))
    assert r.status_code == 201, r.text
    assert str(api.vistas[0].url) == "https://viacep.test/ws/1/json/?campos=uf%2Ccep"


# ---------- SSRF e montagem ----------


async def test_url_para_ip_interno_e_recusada(client, api):
    uid, h = await usuario(client)
    r = await cadastrar(client, h, viacep(url="https://interno.test/ws/{cep}/json/"))
    assert r.status_code == 422 and "10.0.0.5" in r.json()["detail"]
    assert api.vistas == [] and await contagens(uid) == (0, 0)


async def test_placeholder_no_host_e_recusado(client, api):
    _, h = await usuario(client)
    r = await cadastrar(client, h, viacep(url="https://{cep}/json/", exemplo={"cep": "interno.test"}))
    assert r.status_code == 422
    assert api.vistas == []


async def test_redirect_para_ip_interno_e_recusado(client, usar_rotas):
    def responder(req):
        if req.url.host == "viacep.test":
            return httpx.Response(302, headers={"location": "https://interno.test/segredo"})
        return httpx.Response(200, json={"vazou": True})

    api = usar_rotas(Api(responder))
    uid, h = await usuario(client)

    r = await cadastrar(client, h, viacep())

    assert r.status_code == 422 and "10.0.0.5" in r.json()["detail"]
    assert [q.url.host for q in api.vistas] == ["viacep.test"]
    assert await contagens(uid) == (0, 0)


async def test_valor_com_barra_espaco_e_interrogacao_e_encodado_no_path(client, api):
    _, h = await usuario(client)

    r = await client.post("/api/api-tools/testar", json=viacep(exemplo={"cep": "a/b c?d"}), headers=h)

    assert r.status_code == 200, r.text
    [req] = api.vistas
    assert req.url.host == "viacep.test"
    assert req.url.raw_path == b"/ws/a%2Fb%20c%3Fd/json/"


async def test_corpo_post_sai_com_os_tipos_certos(client, api):
    _, h = await usuario(client)
    params = [
        {"nome": "lat", "tipo": "number", "descricao": "", "obrigatorio": True},
        {"nome": "n", "tipo": "integer", "descricao": "", "obrigatorio": True},
        {"nome": "ok", "tipo": "boolean", "descricao": "", "obrigatorio": True},
        {"nome": "nome", "tipo": "string", "descricao": "", "obrigatorio": True},
    ]
    body = viacep(
        metodo="POST",
        url="https://viacep.test/consulta",
        parametros=params,
        corpo={"lat": "{lat}", "filtro": {"n": "{n}", "ok": "{ok}"}, "saudacao": "Olá {nome}"},
        exemplo={"lat": -23.5, "n": "3", "ok": True, "nome": "Ana"},
    )

    r = await client.post("/api/api-tools/testar", json=body, headers=h)

    assert r.status_code == 200, r.text
    [req] = api.vistas
    assert req.method == "POST"
    assert json.loads(req.content) == {"lat": -23.5, "filtro": {"n": 3, "ok": True}, "saudacao": "Olá Ana"}


async def test_testar_devolve_status_corpo_e_ms_sem_gravar(client, usar_rotas):
    usar_rotas(Api(lambda _req: httpx.Response(404, text="nada")))
    uid, h = await usuario(client)

    r = await client.post("/api/api-tools/testar", json=viacep(), headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["status"] == 404 and r.json()["corpo_cortado"] == "nada" and r.json()["ms"] >= 0
    assert await contagens(uid) == (0, 0)


# ---------- Auth ----------


@pytest.mark.parametrize(
    ("auth", "header", "valor"),
    [
        ({"tipo": "header", "nome": "X-Api-Key", "valor": SEGREDO}, "x-api-key", SEGREDO),
        ({"tipo": "bearer", "token": SEGREDO}, "authorization", f"Bearer {SEGREDO}"),
    ],
)
async def test_auth_chega_no_request_e_nunca_volta(client, api, auth, header, valor):
    uid, h = await usuario(client)

    r = await cadastrar(client, h, viacep(auth=auth))

    assert r.status_code == 201, r.text
    assert api.vistas[0].headers[header] == valor
    assert SEGREDO not in r.text
    lista = await client.get("/api/api-tools", headers=h)
    assert SEGREDO not in lista.text and lista.json()[0]["auth_tipo"] == auth["tipo"]
    async with SessionLocal() as s:
        guardado = await s.scalar(text("SELECT auth FROM api_tools WHERE user_id = :u"), {"u": uid})
    assert SEGREDO not in guardado
    [ev] = await eventos("api_tool_added", user_id=uid)
    assert SEGREDO not in json.dumps(ev.payload)


# ---------- Registro por Conversa e turno ----------


async def test_tool_de_api_so_aparece_para_o_dono(client, api):
    _, h_dono = await usuario(client)
    _, h_outro = await usuario(client)
    nome = (await cadastrar(client, h_dono, viacep())).json()["tool_nome"]
    cid_dono = (await criar(client, h_dono))["id"]
    cid_outro = (await criar(client, h_outro))["id"]

    def nomes(r) -> set[str]:
        return {t["nome"] for t in r.json()}

    da_conversa = (await client.get(f"/api/conversations/{cid_dono}/tools", headers=h_dono)).json()
    assert {t["nome"] for t in da_conversa if t["origem"] == "api"} == {nome}
    assert nome not in nomes(await client.get(f"/api/conversations/{cid_outro}/tools", headers=h_outro))
    assert nome not in nomes(await client.get("/api/tools", headers=h_outro))
    assert (await client.get("/api/api-tools", headers=h_outro)).json() == []


async def test_turno_chama_tool_de_api_e_recebe_json_compacto(client, api, usar_modelo):
    uid, h = await usuario(client)
    nome = (await cadastrar(client, h, viacep())).json()["tool_nome"]
    usar_modelo(modelo_que_chama(nome, {"cep": "20040002"}, []))
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("qual o endereço do CEP 20040002?"), headers=h)

    assert r.status_code == 200, r.text
    assert str(api.vistas[-1].url) == "https://viacep.test/ws/20040002/json/"
    assert await ultima_resposta(client, h, cid) == 'Resposta: {"cep":"01001-000","uf":"SP"}'
    [ev] = await eventos("tool_call", user_id=uid)
    assert ev.payload["tool"] == nome and ev.payload["origem"] == "api"


async def test_resposta_500_no_turno_vira_texto_sem_quebrar(client, api, usar_modelo):
    _, h = await usuario(client)
    nome = (await cadastrar(client, h, viacep())).json()["tool_nome"]
    api.responder = lambda _req: httpx.Response(500, text="erro interno")
    usar_modelo(modelo_que_chama(nome, {"cep": "1"}, []))
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("cep 1"), headers=h)

    assert r.status_code == 200, r.text
    assert await ultima_resposta(client, h, cid) == "Resposta: A API respondeu 500: erro interno"


async def test_remover_apaga_tool_e_audita(client, api):
    uid, h = await usuario(client)
    out = (await cadastrar(client, h, viacep())).json()
    _, h_outro = await usuario(client)
    assert (await client.delete(f"/api/api-tools/{out['id']}", headers=h_outro)).status_code == 404

    r = await client.delete(f"/api/api-tools/{out['id']}", headers=h)

    assert r.status_code == 204
    assert await contagens(uid) == (0, 0)
    async with SessionLocal() as s:
        assert await s.get(Tool, out["tool_nome"]) is None
    [ev] = await eventos("api_tool_removed", user_id=uid)
    assert ev.payload["tool"] == out["tool_nome"]


async def test_nome_repetido_do_mesmo_usuario_da_409(client, api):
    _, h = await usuario(client)
    assert (await cadastrar(client, h, viacep())).status_code == 201
    assert (await cadastrar(client, h, viacep())).status_code == 409


async def test_modelos_prontos_tem_definicao_completa(client):
    _, h = await usuario(client)
    r = await client.get("/api/api-tools/modelos", headers=h)
    assert r.status_code == 200
    modelos = r.json()
    assert [m["nome"] for m in modelos] == ["viacep", "open_meteo", "cnpj"]
    assert all(m["exemplo"] and m["parametros"] and m["url"].startswith("https://") for m in modelos)
