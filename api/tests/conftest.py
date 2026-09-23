"""Fixtures compartilhadas. Exigem o Postgres do compose de pé e migrado."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app
from app.roteador import cliente_jev


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def session():
    async with SessionLocal() as s:
        yield s


@pytest.fixture(autouse=True)
def sem_fallback_real(monkeypatch):
    """Nenhum teste cai no Gemini de reserva real nem espera o backoff. test_resiliencia troca."""
    from app import resiliencia
    from app.chat import modelo_reserva

    async def ja(_s: float) -> None:
        return None

    monkeypatch.setattr(resiliencia, "dormir", ja)
    app.dependency_overrides[modelo_reserva] = lambda: None
    yield
    app.dependency_overrides.pop(modelo_reserva, None)


@pytest.fixture(autouse=True)
def sem_jev():
    """Nenhum teste chama o Jev real. Sem cliente, o Roteador cai em AUTO. test_roteador troca."""
    app.dependency_overrides[cliente_jev] = lambda: None
    yield
    app.dependency_overrides.pop(cliente_jev, None)
