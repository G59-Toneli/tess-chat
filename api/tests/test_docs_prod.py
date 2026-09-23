"""/docs, /redoc e /openapi.json só fora de prod. O app é montado no import, então prod roda em subprocesso."""

import os
import subprocess
import sys

SCRIPT = """
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/openapi.json")
        print("openapi", r.headers.get("content-type", "").startswith("application/json"))
        print("docs", "swagger-ui" in (await c.get("/docs")).text)
        print("redoc", "redoc" in (await c.get("/redoc")).text)

asyncio.run(main())
"""


def rodar(env: str) -> str:
    extra = {"ENV": env, "JWT_SECRET": "x" * 40}
    r = subprocess.run([sys.executable, "-c", SCRIPT], env={**os.environ, **extra}, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_prod_nao_publica_o_schema_da_api():
    assert rodar("prod").split() == ["openapi", "False", "docs", "False", "redoc", "False"]


def test_dev_publica_o_schema_da_api():
    assert rodar("dev").split() == ["openapi", "True", "docs", "True", "redoc", "True"]
