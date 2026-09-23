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
def sem_jev():
    """Nenhum teste chama o Jev real. Sem cliente, o Roteador cai em AUTO. test_roteador troca."""
    app.dependency_overrides[cliente_jev] = lambda: None
    yield
    app.dependency_overrides.pop(cliente_jev, None)
