import uuid

from app.audit import AuditEvent, audit
from app.db import SessionLocal

USER = uuid.UUID("11111111-1111-1111-1111-111111111111")
CONVERSA = uuid.UUID("22222222-2222-2222-2222-222222222222")


async def test_audit_grava_evento_que_pode_ser_lido_de_volta(session):
    evento = await audit(
        session,
        "model_call",
        user_id=USER,
        conversation_id=CONVERSA,
        payload={"turno": 1},
        input_tokens=120,
        output_tokens=45,
        cost_micro_usd=987,
        latency_ms=830,
        model="gemini-3.8-flash",
    )
    await session.commit()

    async with SessionLocal() as outra:
        lido = await outra.get(AuditEvent, evento.id)

    assert lido is not None
    assert lido.event_type == "model_call"
    assert lido.user_id == USER
    assert lido.conversation_id == CONVERSA
    assert lido.payload == {"turno": 1}
    assert (lido.input_tokens, lido.output_tokens) == (120, 45)
    assert lido.cost_micro_usd == 987
    assert lido.latency_ms == 830
    assert lido.model == "gemini-3.8-flash"
    assert lido.ts is not None


async def test_audit_sem_payload_grava_objeto_vazio(session):
    evento = await audit(session, "login_ok")
    await session.commit()

    async with SessionLocal() as outra:
        lido = await outra.get(AuditEvent, evento.id)

    assert lido.payload == {}
    assert lido.user_id is None
