import uuid

from sqlalchemy import select

from app.audit import AuditEvent
from app.auth import DEMO_EMAIL, garantir_conta_demo
from app.config import settings
from app.db import SessionLocal

SENHA = "senha-forte-123"


def email_novo() -> str:
    return f"u-{uuid.uuid4().hex[:10]}@example.com"


async def registrar(client, email: str) -> dict:
    resp = await client.post("/auth/register", json={"email": email, "password": SENHA})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def logar(client, email: str, senha: str = SENHA):
    return await client.post("/auth/jwt/login", data={"username": email, "password": senha})


async def eventos(event_type: str, **filtro) -> list[AuditEvent]:
    async with SessionLocal() as s:
        q = select(AuditEvent).where(AuditEvent.event_type == event_type)
        if "user_id" in filtro:
            q = q.where(AuditEvent.user_id == filtro["user_id"])
        if "email" in filtro:
            q = q.where(AuditEvent.payload["email"].astext == filtro["email"])
        return list((await s.scalars(q)).all())


async def test_registra_loga_e_acessa_rota_protegida(client):
    email = email_novo()
    user = await registrar(client, email)

    login = await logar(client, email)
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]
    assert me.json()["email"] == email


async def test_rota_protegida_sem_token_recusa(client):
    resp = await client.get("/users/me")

    assert resp.status_code == 401


async def test_rota_protegida_com_token_invalido_recusa(client):
    resp = await client.get("/users/me", headers={"Authorization": "Bearer lixo"})

    assert resp.status_code == 401


async def test_registro_gera_evento_user_registered(client):
    email = email_novo()
    user = await registrar(client, email)

    assert len(await eventos("user_registered", user_id=uuid.UUID(user["id"]))) == 1


async def test_login_ok_gera_evento_com_user_id(client):
    email = email_novo()
    user = await registrar(client, email)

    await logar(client, email)
    await logar(client, email)

    assert len(await eventos("login_ok", user_id=uuid.UUID(user["id"]))) == 2


async def test_senha_errada_recusa_e_gera_login_failed(client):
    email = email_novo()
    await registrar(client, email)

    resp = await logar(client, email, "senha-errada")

    assert resp.status_code == 400
    falhas = await eventos("login_failed", email=email)
    assert len(falhas) == 1
    assert "senha-errada" not in str(falhas[0].payload)


async def test_email_inexistente_gera_login_failed(client):
    email = email_novo()

    resp = await logar(client, email)

    assert resp.status_code == 400
    assert len(await eventos("login_failed", email=email)) == 1


async def test_conta_demo_existe_e_loga_apos_seed(client):
    await garantir_conta_demo()
    await garantir_conta_demo()  # idempotente

    resp = await logar(client, DEMO_EMAIL, settings.demo_password)

    assert resp.status_code == 200


async def test_config_publica_em_prod_esconde_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "env", "prod")

    resp = await client.get("/api/config-publica")

    assert resp.status_code == 200
    assert resp.json() == {"demo": False, "env": "prod"}


async def test_config_publica_em_dev_mostra_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "env", "dev")

    resp = await client.get("/api/config-publica")

    assert resp.status_code == 200
    assert resp.json() == {"demo": True, "env": "dev"}


async def test_em_prod_login_da_conta_demo_continua_aceito(client, monkeypatch):
    monkeypatch.setattr(settings, "env", "prod")
    await garantir_conta_demo()

    resp = await logar(client, DEMO_EMAIL, settings.demo_password)

    assert resp.status_code == 200
