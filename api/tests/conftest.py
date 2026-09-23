"""Fixtures compartilhadas. Exigem o Postgres do compose de pé e migrado."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def session():
    async with SessionLocal() as s:
        yield s
