import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.audit import audit

COMANDOS_PROIBIDOS = [
    "UPDATE audit_events SET event_type = 'adulterado' WHERE id = :id",
    "DELETE FROM audit_events WHERE id = :id",
]


async def test_sessao_da_app_roda_como_tess_app(session):
    assert (await session.scalar(text("SELECT current_user"))) == "tess_app"


@pytest.mark.parametrize("sql", COMANDOS_PROIBIDOS, ids=["update", "delete"])
async def test_tess_app_nao_altera_nem_apaga_evento(session, sql):
    evento = await audit(session, "login_ok")
    await session.commit()

    with pytest.raises(DBAPIError) as erro:
        await session.execute(text(sql), {"id": evento.id})

    assert isinstance(erro.value.orig.__cause__, asyncpg.InsufficientPrivilegeError)
