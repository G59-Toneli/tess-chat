"""Envio de e-mail com confirmação (ticket 25, ADR 0013). Google atrás do MockTransport do test_conectores."""

import base64
import email
import json
from email import policy

from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.chat import MODELO
from app.conectores import transporte_google
from app.main import app
from app.tools import transporte
from tests.test_auth import eventos
from tests.test_chat import corpo, usar_modelo  # noqa: F401  (fixture)
from tests.test_conectores import LEITURA, Google, conectar, google, modelo_que_chama  # noqa: F401  (fixture)
from tests.test_conversas import criar, usuario

ARGS = {"para": "ana@exemplo.com", "assunto": "Re: Fatura de setembro", "corpo": "Confirmo a reunião.", "thread_id": "t1"}
DRAFTS = "/api/connectors/google/drafts"


def envios(g: Google) -> list:
    return [r for r in g.vistas if r.url.path == "/gmail/v1/users/me/messages/send"]


def mime_do(envio) -> tuple[dict, email.message.EmailMessage]:
    body = json.loads(envio.content)
    return body, email.message_from_bytes(base64.urlsafe_b64decode(body["raw"]), policy=policy.default)


async def tools_da_conversa(client, h, cid) -> dict[str, bool]:
    r = await client.get(f"/api/conversations/{cid}/tools", headers=h)
    return {t["nome"]: t["ativa"] for t in r.json()}


async def parte_do_rascunho(client, h, cid) -> dict:
    """Parte tool-gmail_send gravada na Mensagem do assistente: é o que o front renderiza."""
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    return next(p for m in msgs for p in m["parts"] if p.get("type") == "tool-gmail_send")


async def rascunho(client, h, usar_modelo, args=ARGS) -> tuple[str, str]:
    """Conecta, liga gmail_send, roda um turno que chama a Tool. Devolve (cid, draft_id)."""
    usar_modelo(modelo_que_chama("gmail_send", args, []))
    await conectar(client, h)
    cid = (await criar(client, h))["id"]
    r = await client.put(f"/api/conversations/{cid}/tools", json={"gmail_send": True}, headers=h)
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/chat/{cid}", json=corpo("responde a Ana confirmando a reunião"), headers=h)
    assert r.status_code == 200, r.text
    parte = await parte_do_rascunho(client, h, cid)
    return cid, parte["output"]["draft_id"]


# ---------- Registro ----------


async def test_gmail_send_nasce_ligada(client, google):
    _, h = await usuario(client)
    await conectar(client, h)
    cid = (await criar(client, h))["id"]

    tools = await tools_da_conversa(client, h, cid)

    assert tools["gmail_send"] is True
    assert tools["gmail_search"] is True


async def test_conector_sem_escopo_de_envio_nao_tem_gmail_send(client, usar_modelo):
    g = Google(escopos=LEITURA)
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    try:
        vistos: list[AgentInfo] = []
        usar_modelo(modelo_que_chama("gmail_send", ARGS, vistos))
        _, h = await usuario(client)
        await conectar(client, h)
        cid = (await criar(client, h))["id"]
        await client.put(f"/api/conversations/{cid}/tools", json={"gmail_send": True}, headers=h)
        await client.post(f"/api/chat/{cid}", json=corpo("responde a Ana"), headers=h)
        tools = await tools_da_conversa(client, h, cid)
    finally:
        app.dependency_overrides.pop(transporte_google, None)
        app.dependency_overrides.pop(transporte, None)

    assert "gmail_send" not in tools
    nomes = {t.name for t in vistos[0].function_tools}
    assert "gmail_send" not in nomes and "gmail_search" in nomes
    assert envios(g) == []


# ---------- Rascunho ----------


async def test_turno_com_gmail_send_cria_rascunho_e_nao_envia(client, google, usar_modelo):
    uid, h = await usuario(client)

    cid, did = await rascunho(client, h, usar_modelo)

    assert envios(google) == []
    parte = await parte_do_rascunho(client, h, cid)
    assert parte["output"]["estado"] == "pendente"
    assert "aguardando confirmação" in parte["output"]["aviso"]
    r = await client.get(f"{DRAFTS}/{did}", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estado"] == "pendente" and d["para"] == "ana@exemplo.com" and d["thread_id"] == "t1"
    assert d["em_resposta"] is True
    [ev] = await eventos("email_draft_created", user_id=uid)
    assert str(ev.conversation_id) == cid and ev.payload["draft_id"] == did


async def test_pode_enviar_no_chat_nao_muda_o_rascunho(client, google, usar_modelo):
    _, h = await usuario(client)
    cid, did = await rascunho(client, h, usar_modelo)
    vistos: list[AgentInfo] = []

    async def so_texto(msgs: list[ModelMessage], info: AgentInfo):
        vistos.append(info)
        yield "Enviado!"  # o modelo pode até afirmar, mas não tem Tool que envie

    usar_modelo(FunctionModel(stream_function=so_texto, model_name=MODELO))
    r = await client.post(f"/api/chat/{cid}", json=corpo("pode enviar"), headers=h)

    assert r.status_code == 200, r.text
    assert (await client.get(f"{DRAFTS}/{did}", headers=h)).json()["estado"] == "pendente"
    assert envios(google) == []
    declarada = next(t for t in vistos[0].function_tools if t.name == "gmail_send")
    assert "NÃO envia" in (declarada.description or "")  # o modelo recebe descricao, não descricao_usuario


# ---------- Enviar e descartar ----------


async def test_enviar_pelo_dono_manda_na_thread(client, google, usar_modelo):
    uid, h = await usuario(client)
    _, did = await rascunho(client, h, usar_modelo, {**ARGS, "assunto": "Re: Reunião de sexta"})

    r = await client.post(f"{DRAFTS}/{did}/enviar", headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "enviado"
    [envio] = envios(google)
    body, mime = mime_do(envio)
    assert body["threadId"] == "t1"
    assert mime["To"] == "ana@exemplo.com"
    assert mime["Subject"] == "Re: Reunião de sexta"
    assert mime["In-Reply-To"] == "<fatura-set@exemplo.com>"
    assert mime["References"] == "<primeiro@exemplo.com> <fatura-set@exemplo.com>"
    assert "Confirmo a reunião." in mime.get_content()
    [ev] = await eventos("email_sent", user_id=uid)
    assert ev.payload["message_id"] == "enviado-1" and ev.payload["draft_id"] == did


async def test_segundo_clique_nao_envia_de_novo(client, google, usar_modelo):
    _, h = await usuario(client)
    _, did = await rascunho(client, h, usar_modelo)

    await client.post(f"{DRAFTS}/{did}/enviar", headers=h)
    r = await client.post(f"{DRAFTS}/{did}/enviar", headers=h)

    assert r.status_code == 409
    assert len(envios(google)) == 1


async def test_sem_thread_envia_sem_cabecalho_de_resposta(client, google, usar_modelo):
    _, h = await usuario(client)
    args = {k: v for k, v in ARGS.items() if k != "thread_id"} | {"assunto": "Oi"}
    _, did = await rascunho(client, h, usar_modelo, args)

    r = await client.post(f"{DRAFTS}/{did}/enviar", headers=h)

    assert r.status_code == 200, r.text
    body, mime = mime_do(envios(google)[0])
    assert "threadId" not in body
    assert mime["In-Reply-To"] is None


async def test_outro_usuario_recebe_404(client, google, usar_modelo):
    _, h = await usuario(client)
    _, did = await rascunho(client, h, usar_modelo)
    _, intruso = await usuario(client)

    ler = await client.get(f"{DRAFTS}/{did}", headers=intruso)
    enviar = await client.post(f"{DRAFTS}/{did}/enviar", headers=intruso)
    descartar = await client.post(f"{DRAFTS}/{did}/descartar", headers=intruso)

    assert (ler.status_code, enviar.status_code, descartar.status_code) == (404, 404, 404)
    assert envios(google) == []
    assert (await client.get(f"{DRAFTS}/{did}", headers=h)).json()["estado"] == "pendente"


async def test_descartar_fecha_o_rascunho(client, google, usar_modelo):
    uid, h = await usuario(client)
    _, did = await rascunho(client, h, usar_modelo)

    r = await client.post(f"{DRAFTS}/{did}/descartar", headers=h)
    depois = await client.post(f"{DRAFTS}/{did}/enviar", headers=h)

    assert r.status_code == 200 and r.json()["estado"] == "descartado"
    assert depois.status_code == 409
    assert envios(google) == []
    [ev] = await eventos("email_draft_discarded", user_id=uid)
    assert ev.payload["draft_id"] == did


async def test_erro_do_gmail_mantem_pendente_com_texto_legivel(client, google, usar_modelo):
    _, h = await usuario(client)
    _, did = await rascunho(client, h, usar_modelo)
    google.envio_status = 403

    r = await client.post(f"{DRAFTS}/{did}/enviar", headers=h)

    assert r.status_code == 502
    assert "insufficient authentication scopes" in r.json()["detail"]
    assert (await client.get(f"{DRAFTS}/{did}", headers=h)).json()["estado"] == "pendente"


# ---------- gmail_read ----------


async def test_gmail_read_devolve_ids_para_responder(client, google, usar_modelo):
    usar_modelo(modelo_que_chama("gmail_read", {"message_id": "m1"}, []))
    _, h = await usuario(client)
    await conectar(client, h)
    cid = (await criar(client, h))["id"]

    await client.post(f"/api/chat/{cid}", json=corpo("lê esse e-mail"), headers=h)

    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    texto = msgs[-1]["parts"][-1]["text"]
    assert "thread_id: t1" in texto and "message_id: m1" in texto
