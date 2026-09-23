import uuid

from app.conectores import EmailDraft
from app.conversas import Message
from app.db import SessionLocal
from tests.test_auth import eventos
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
