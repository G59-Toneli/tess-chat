import uuid

from sqlalchemy import select

from app.conversas import Message
from app.db import SessionLocal
from tests.test_auth import email_novo, eventos, logar, registrar


async def usuario(client) -> tuple[uuid.UUID, dict]:
    """Registra, loga e devolve (id, headers)."""
    email = email_novo()
    user = await registrar(client, email)
    token = (await logar(client, email)).json()["access_token"]
    return uuid.UUID(user["id"]), {"Authorization": f"Bearer {token}"}


async def criar(client, headers, titulo: str | None = None) -> dict:
    body = {"title": titulo} if titulo else {}
    resp = await client.post("/api/conversations", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_sem_token_recusa(client):
    assert (await client.get("/api/conversations")).status_code == 401


async def test_cria_lista_renomeia_apaga(client):
    _, h = await usuario(client)

    conv = await criar(client, h, "Primeira")
    lista = (await client.get("/api/conversations", headers=h)).json()
    assert [c["id"] for c in lista] == [conv["id"]]
    assert lista[0]["title"] == "Primeira"

    resp = await client.patch(f"/api/conversations/{conv['id']}", json={"title": "Nova"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Nova"

    assert (await client.delete(f"/api/conversations/{conv['id']}", headers=h)).status_code == 204
    assert (await client.get("/api/conversations", headers=h)).json() == []
    assert (await client.get(f"/api/conversations/{conv['id']}", headers=h)).status_code == 404


async def test_titulo_padrao(client):
    _, h = await usuario(client)

    assert (await criar(client, h))["title"] == "Nova conversa"


async def test_usuario_nao_ve_conversa_de_outro(client):
    _, ha = await usuario(client)
    _, hb = await usuario(client)
    conv = await criar(client, ha, "Segredo de A")
    url = f"/api/conversations/{conv['id']}"

    assert (await client.get("/api/conversations", headers=hb)).json() == []
    assert (await client.get(url, headers=hb)).status_code == 404
    assert (await client.get(f"{url}/messages", headers=hb)).status_code == 404
    assert (await client.patch(url, json={"title": "x"}, headers=hb)).status_code == 404
    assert (await client.delete(url, headers=hb)).status_code == 404
    # Continua intacta para A.
    assert (await client.get(url, headers=ha)).json()["title"] == "Segredo de A"


async def test_mensagens_voltam_na_ordem_de_criacao(client):
    _, h = await usuario(client)
    conv = await criar(client, h)
    cid = uuid.UUID(conv["id"])
    textos = ["um", "dois", "três"]
    # Mesma transação: created_at igual nas três. A ordem tem que vir do id.
    async with SessionLocal() as s:
        for i, t in enumerate(textos):
            s.add(Message(conversation_id=cid, role="user" if i % 2 == 0 else "assistant",
                          parts=[{"type": "text", "text": t}]))
        await s.commit()

    resp = await client.get(f"/api/conversations/{cid}/messages", headers=h)

    assert resp.status_code == 200
    msgs = resp.json()
    assert [m["parts"][0]["text"] for m in msgs] == textos
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]


async def test_eventos_de_criacao_e_remocao(client):
    uid, h = await usuario(client)
    conv = await criar(client, h)
    cid = uuid.UUID(conv["id"])

    await client.delete(f"/api/conversations/{cid}", headers=h)

    criados = await eventos("conversation_created", user_id=uid)
    apagados = await eventos("conversation_deleted", user_id=uid)
    assert [e.conversation_id for e in criados] == [cid]
    assert [e.conversation_id for e in apagados] == [cid]


async def test_apagar_conversa_leva_as_mensagens(client):
    _, h = await usuario(client)
    cid = uuid.UUID((await criar(client, h))["id"])
    async with SessionLocal() as s:
        s.add(Message(conversation_id=cid, role="user", parts=[{"type": "text", "text": "oi"}]))
        await s.commit()

    await client.delete(f"/api/conversations/{cid}", headers=h)

    async with SessionLocal() as s:
        restantes = await s.scalars(select(Message).where(Message.conversation_id == cid))
        assert restantes.all() == []
