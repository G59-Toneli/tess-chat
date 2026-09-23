import uuid

import pytest
from pydantic_ai.messages import BinaryContent
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import update

from app.chat import MODELO
from app.conectores import EmailDraft
from app.config import settings
from app.conversas import Attachment, Message
from app.db import SessionLocal
from tests.test_anexos import PNG, conteudo_do_usuario, subir
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_chat import textos as textos_modelo
from tests.test_credito import linhas
from tests.test_conversas import criar, usuario


async def mensagem(cid: str, role: str, texto: str) -> None:
    async with SessionLocal() as s:
        s.add(Message(conversation_id=uuid.UUID(cid), role=role, parts=[{"type": "text", "text": texto}]))
        await s.commit()


def textos(corpo: dict) -> list[str]:
    return [m["parts"][0]["text"] for m in corpo["messages"]]


async def compartilhar(client, h, cid: str) -> dict:
    resp = await client.post(f"/api/conversations/{cid}/share", headers=h)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_link_abre_sem_login_e_corta_na_ultima_mensagem(client):
    uid, h = await usuario(client)
    conv = await criar(client, h, "Receita de bolo")
    await mensagem(conv["id"], "user", "como faço bolo?")
    await mensagem(conv["id"], "assistant", "farinha, ovo, açúcar")

    share = await compartilhar(client, h, conv["id"])
    await mensagem(conv["id"], "user", "depois do share")

    resp = await client.get(f"/api/s/{share['id']}")  # sem Authorization
    assert resp.status_code == 200
    assert resp.headers["x-robots-tag"] == "noindex"
    corpo = resp.json()
    assert corpo["title"] == "Receita de bolo"
    assert textos(corpo) == ["como faço bolo?", "farinha, ovo, açúcar"]
    assert [e.conversation_id for e in await eventos("share_created", user_id=uid)] == [uuid.UUID(conv["id"])]


async def test_id_tem_128_bits_ou_mais(client):
    _, h = await usuario(client)
    conv = await criar(client, h)
    share = await compartilhar(client, h, conv["id"])
    # token_urlsafe: 6 bits por caractere.
    assert len(share["id"]) * 6 >= 128
    assert share["url"] == f"/s/{share['id']}"


async def test_revogado_e_inexistente_devolvem_404_identicos(client):
    uid, h = await usuario(client)
    conv = await criar(client, h)
    await mensagem(conv["id"], "user", "oi")
    share = await compartilhar(client, h, conv["id"])

    assert (await client.delete(f"/api/shares/{share['id']}", headers=h)).status_code == 204
    assert len(await eventos("share_revoked", user_id=uid)) == 1

    for rota in ("/api/s/", "/s/"):
        revogado = await client.get(f"{rota}{share['id']}")
        inexistente = await client.get(f"{rota}naoexiste{uuid.uuid4().hex}")
        assert revogado.status_code == inexistente.status_code == 404
        assert revogado.content == inexistente.content
        assert revogado.headers["content-type"] == inexistente.headers["content-type"]
        assert revogado.headers["x-robots-tag"] == inexistente.headers["x-robots-tag"] == "noindex"


async def test_rota_do_front_serve_com_noindex(client):
    _, h = await usuario(client)
    conv = await criar(client, h)
    share = await compartilhar(client, h, conv["id"])

    resp = await client.get(f"/s/{share['id']}")
    assert resp.status_code == 200
    assert resp.headers["x-robots-tag"] == "noindex"
    assert "text/html" in resp.headers["content-type"]


async def test_meus_links_lista_so_os_ativos_do_usuario(client):
    _, ha = await usuario(client)
    _, hb = await usuario(client)
    conv = await criar(client, ha, "Minha")
    s1 = await compartilhar(client, ha, conv["id"])
    s2 = await compartilhar(client, ha, conv["id"])
    await client.delete(f"/api/shares/{s1['id']}", headers=ha)

    lista = (await client.get("/api/shares", headers=ha)).json()
    assert [(s["id"], s["title"]) for s in lista] == [(s2["id"], "Minha")]
    assert (await client.get("/api/shares", headers=hb)).json() == []


async def test_outro_usuario_nao_compartilha_nem_revoga(client):
    _, ha = await usuario(client)
    _, hb = await usuario(client)
    conv = await criar(client, ha)
    share = await compartilhar(client, ha, conv["id"])

    assert (await client.post(f"/api/conversations/{conv['id']}/share", headers=hb)).status_code == 404
    assert (await client.delete(f"/api/shares/{share['id']}", headers=hb)).status_code == 404
    assert (await client.get(f"/api/s/{share['id']}")).status_code == 200


async def test_apagar_conversa_derruba_o_link(client):
    _, h = await usuario(client)
    conv = await criar(client, h)
    share = await compartilhar(client, h, conv["id"])
    await client.delete(f"/api/conversations/{conv['id']}", headers=h)

    assert (await client.get(f"/api/s/{share['id']}")).status_code == 404


async def test_criar_e_revogar_exigem_login(client):
    assert (await client.post(f"/api/conversations/{uuid.uuid4()}/share")).status_code == 401
    assert (await client.delete("/api/shares/x")).status_code == 401
    assert (await client.get("/api/shares")).status_code == 401


async def rascunho_na_conversa(uid: uuid.UUID, cid: str, estado: str) -> str:
    """EmailDraft com o estado dado e a Mensagem com a part da tool, gravada em 'pendente' como no chat."""
    async with SessionLocal() as s:
        d = EmailDraft(user_id=uid, conversation_id=uuid.UUID(cid), para="ana@x.com", assunto="Oi", corpo="c", estado=estado)
        s.add(d)
        await s.flush()
        saida = {"draft_id": str(d.id), "estado": "pendente", "para": "ana@x.com", "assunto": "Oi", "corpo": "c", "thread_id": None}
        parte = {"type": "tool-gmail_send", "toolCallId": "c1", "state": "output-available", "input": {}, "output": saida}
        s.add(Message(conversation_id=uuid.UUID(cid), role="assistant", parts=[parte]))
        await s.commit()
        return str(d.id)


async def test_link_mostra_o_estado_real_do_rascunho(client):
    uid, h = await usuario(client)
    conv = await criar(client, h)
    await rascunho_na_conversa(uid, conv["id"], "enviado")
    share = await compartilhar(client, h, conv["id"])

    corpo = (await client.get(f"/api/s/{share['id']}")).json()
    assert corpo["messages"][0]["parts"][0]["output"]["estado"] == "enviado"


async def test_link_nao_le_rascunho_de_outra_conversa(client):
    uid, h = await usuario(client)
    outra = await criar(client, h)
    draft_id = await rascunho_na_conversa(uid, outra["id"], "enviado")
    conv = await criar(client, h)
    # Part que aponta para o rascunho de outra Conversa: fica como gravada.
    parte = {"type": "tool-gmail_send", "toolCallId": "c9", "state": "output-available", "input": {}, "output": {"draft_id": draft_id, "estado": "pendente"}}
    async with SessionLocal() as s:
        s.add(Message(conversation_id=uuid.UUID(conv["id"]), role="assistant", parts=[parte]))
        await s.commit()
    share = await compartilhar(client, h, conv["id"])

    corpo = (await client.get(f"/api/s/{share['id']}")).json()
    assert corpo["messages"][0]["parts"][0]["output"]["estado"] == "pendente"


# --- Ticket 46: continuar a conversa do link (fork) ---

async def fork(client, h, share_id: str) -> str:
    resp = await client.post(f"/api/s/{share_id}/fork", headers=h)
    assert resp.status_code == 201, resp.text
    return resp.json()["conversation_id"]


async def partes(client, h, cid: str) -> list[list[dict]]:
    return [m["parts"] for m in (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()]


async def test_fork_copia_ate_o_corte_e_nao_altera_a_do_dono(client):
    _, hd = await usuario(client)
    vid, hv = await usuario(client)
    conv = await criar(client, hd, "Receita")
    await mensagem(conv["id"], "user", "como faço bolo?")
    await mensagem(conv["id"], "assistant", "farinha, ovo")
    share = await compartilhar(client, hd, conv["id"])
    await mensagem(conv["id"], "user", "depois do share")

    nova = await fork(client, hv, share["id"])

    copia = (await client.get(f"/api/conversations/{nova}", headers=hv)).json()
    assert copia["title"] == "Receita (cópia)"
    assert [p[0]["text"] for p in await partes(client, hv, nova)] == ["como faço bolo?", "farinha, ovo"]
    assert [p[0]["text"] for p in await partes(client, hd, conv["id"])] == ["como faço bolo?", "farinha, ovo", "depois do share"]
    assert (await client.get(f"/api/conversations/{nova}", headers=hd)).status_code == 404
    [ev] = await eventos("share_forked", user_id=vid)
    assert ev.conversation_id == uuid.UUID(nova)
    assert ev.payload == {"share_id": share["id"], "conversa_origem": conv["id"], "conversa_nova": nova, "anexos_copiados": []}


async def test_fork_de_revogado_ou_inexistente_e_404_e_sem_login_401(client):
    _, hd = await usuario(client)
    _, hv = await usuario(client)
    conv = await criar(client, hd)
    share = await compartilhar(client, hd, conv["id"])
    await client.delete(f"/api/shares/{share['id']}", headers=hd)

    assert (await client.post(f"/api/s/{share['id']}/fork", headers=hv)).status_code == 404
    assert (await client.post(f"/api/s/naoexiste{uuid.uuid4().hex}/fork", headers=hv)).status_code == 404
    assert (await client.post(f"/api/s/{share['id']}/fork")).status_code == 401
    assert (await client.get("/api/conversations", headers=hv)).json() == []


async def test_dono_faz_fork_do_proprio_link(client):
    _, h = await usuario(client)
    conv = await criar(client, h, "Minha")
    await mensagem(conv["id"], "user", "oi")
    share = await compartilhar(client, h, conv["id"])

    nova = await fork(client, h, share["id"])

    assert nova != conv["id"]
    assert [c["title"] for c in (await client.get("/api/conversations", headers=h)).json()] == ["Minha (cópia)", "Minha"]


async def test_primeiro_turno_na_copia_ve_o_historico_e_cobra_do_visitante(client, usar_modelo):
    vistas = []

    async def stream(msgs, _info):
        vistas.append(msgs)
        yield "continuando"

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))
    did, hd = await usuario(client)
    vid, hv = await usuario(client)
    conv = await criar(client, hd)
    await mensagem(conv["id"], "user", "meu nome é Ana")
    await mensagem(conv["id"], "assistant", "oi Ana")
    share = await compartilhar(client, hd, conv["id"])
    nova = await fork(client, hv, share["id"])
    assert await linhas(user_id=vid) == []

    r = await client.post(f"/api/chat/{nova}", json=corpo("qual meu nome?"), headers=hv)
    assert r.status_code == 200, r.text

    assert textos_modelo(vistas[0]) == [("user", "meu nome é Ana"), ("assistant", "oi Ana"), ("user", "qual meu nome?")]
    assert [str(l.conversation_id) for l in await linhas(user_id=vid)] == [nova]
    assert await linhas(user_id=did) == []


async def test_rascunho_copiado_mostra_estado_e_nao_e_enviavel_pelo_visitante(client):
    did, hd = await usuario(client)
    _, hv = await usuario(client)
    conv = await criar(client, hd)
    draft_id = await rascunho_na_conversa(did, conv["id"], "pendente")
    share = await compartilhar(client, hd, conv["id"])

    nova = await fork(client, hv, share["id"])

    [[parte]] = await partes(client, hv, nova)
    assert parte["output"]["draft_id"] == draft_id
    assert parte["output"]["copia"] is True
    for acao in ("enviar", "descartar"):
        assert (await client.post(f"/api/connectors/google/drafts/{draft_id}/{acao}", headers=hv)).status_code == 404
    assert (await client.get(f"/api/connectors/google/drafts/{draft_id}", headers=hd)).json()["estado"] == "pendente"


async def test_rascunho_copiado_leva_o_estado_real(client):
    did, hd = await usuario(client)
    _, hv = await usuario(client)
    conv = await criar(client, hd)
    await rascunho_na_conversa(did, conv["id"], "enviado")
    share = await compartilhar(client, hd, conv["id"])

    [[parte]] = await partes(client, hv, await fork(client, hv, share["id"]))
    assert parte["output"]["estado"] == "enviado"


async def test_anexo_sem_registro_vira_texto_na_copia(client):
    _, hd = await usuario(client)
    _, hv = await usuario(client)
    conv = await criar(client, hd)
    arquivo = {"type": "file", "url": f"/api/attachments/{uuid.uuid4()}", "mediaType": "image/png", "filename": "foto.png"}
    async with SessionLocal() as s:
        s.add(Message(conversation_id=uuid.UUID(conv["id"]), role="user", parts=[arquivo, {"type": "text", "text": "veja"}]))
        await s.commit()
    share = await compartilhar(client, hd, conv["id"])

    [copiadas] = await partes(client, hv, await fork(client, hv, share["id"]))
    assert copiadas == [{"type": "text", "text": "[anexo: foto.png]"}, {"type": "text", "text": "veja"}]


# --- Ticket 48: imagem no link público e no fork ---

@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", tmp_path)
    return tmp_path


async def imagem_na_conversa(client, h, cid: str) -> dict:
    """Upload real e Mensagem do usuário com a part do arquivo, ligada como o chat liga."""
    a = (await subir(client, h, "foto.png", PNG, "image/png")).json()
    arquivo = {"type": "file", "url": a["url"], "mediaType": "image/png", "filename": "foto.png"}
    async with SessionLocal() as s:
        m = Message(conversation_id=uuid.UUID(cid), role="user", parts=[arquivo, {"type": "text", "text": "veja"}])
        s.add(m)
        await s.flush()
        await s.execute(update(Attachment).where(Attachment.id == uuid.UUID(a["id"])).values(message_id=m.id))
        await s.commit()
    return a


async def test_link_serve_a_imagem_sem_login(client, pasta):
    _, h = await usuario(client)
    conv = await criar(client, h)
    a = await imagem_na_conversa(client, h, conv["id"])
    share = await compartilhar(client, h, conv["id"])

    corpo = (await client.get(f"/api/s/{share['id']}")).json()
    url = corpo["messages"][0]["parts"][0]["url"]
    assert url == f"/api/s/{share['id']}/attachments/{a['id']}"
    resp = await client.get(url)  # sem Authorization
    assert resp.status_code == 200
    assert resp.content == PNG
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["x-robots-tag"] == "noindex"


async def test_imagem_do_link_nega_com_404_identico(client, pasta):
    _, h = await usuario(client)
    outra = await criar(client, h)
    de_outra = await imagem_na_conversa(client, h, outra["id"])
    conv = await criar(client, h)
    antes = await imagem_na_conversa(client, h, conv["id"])
    share = await compartilhar(client, h, conv["id"])
    depois = await imagem_na_conversa(client, h, conv["id"])
    solto = (await subir(client, h, "solto.png", PNG, "image/png")).json()
    revogado = await compartilhar(client, h, conv["id"])
    await client.delete(f"/api/shares/{revogado['id']}", headers=h)

    base = f"/api/s/{share['id']}/attachments"
    negados = [
        f"{base}/{de_outra['id']}",
        f"{base}/{depois['id']}",
        f"{base}/{solto['id']}",
        f"{base}/{uuid.uuid4()}",
        f"/api/s/{revogado['id']}/attachments/{antes['id']}",
        f"/api/s/naoexiste/attachments/{antes['id']}",
    ]
    respostas = [await client.get(u) for u in negados]
    assert [r.status_code for r in respostas] == [404] * len(negados)
    assert {r.content for r in respostas} == {respostas[0].content}
    assert all(r.headers["x-robots-tag"] == "noindex" for r in respostas)
    assert (await client.get(f"{base}/{antes['id']}")).status_code == 200


async def test_fork_copia_o_anexo_para_o_visitante(client, pasta, usar_modelo):
    vistas = []

    async def stream(msgs, _info):
        vistas.append(msgs)
        yield "é um PNG"

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))
    _, hd = await usuario(client)
    vid, hv = await usuario(client)
    conv = await criar(client, hd)
    original = await imagem_na_conversa(client, hd, conv["id"])
    share = await compartilhar(client, hd, conv["id"])

    nova = await fork(client, hv, share["id"])
    [[copia, texto]] = await partes(client, hv, nova)
    novo_id = copia["url"].removeprefix("/api/attachments/")
    assert novo_id != original["id"]
    assert texto == {"type": "text", "text": "veja"}
    baixada = await client.get(copia["url"], headers=hv)
    assert (baixada.status_code, baixada.content) == (200, PNG)
    [ev] = await eventos("share_forked", user_id=vid)
    assert ev.payload["anexos_copiados"] == [novo_id]

    r = await client.post(f"/api/chat/{nova}", json=corpo("o que tem na imagem?"), headers=hv)
    assert r.status_code == 200, r.text
    binarios = [c for c in conteudo_do_usuario(vistas[0]) if isinstance(c, BinaryContent)]
    assert [(b.media_type, b.data) for b in binarios] == [("image/png", PNG)]


async def test_copia_sobrevive_a_revogacao_e_visitante_nao_baixa_o_original(client, pasta):
    _, hd = await usuario(client)
    _, hv = await usuario(client)
    conv = await criar(client, hd)
    original = await imagem_na_conversa(client, hd, conv["id"])
    share = await compartilhar(client, hd, conv["id"])
    [[copia, _]] = await partes(client, hv, await fork(client, hv, share["id"]))
    await client.delete(f"/api/shares/{share['id']}", headers=hd)

    assert (await client.get(copia["url"], headers=hv)).status_code == 200
    assert (await client.get(original["url"], headers=hv)).status_code == 404
    assert (await client.get(f"/api/s/{share['id']}/attachments/{original['id']}")).status_code == 404
