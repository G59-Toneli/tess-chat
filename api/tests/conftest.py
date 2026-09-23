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


# Fixtures usadas por vários módulos. Os helpers que elas usam continuam no módulo de origem.


@pytest.fixture
def usar_modelo():
    """Troca o modelo da rota. Limpa o override no fim."""
    from app.chat import modelo

    def trocar(m):
        app.dependency_overrides[modelo] = lambda: m

    yield trocar
    app.dependency_overrides.pop(modelo, None)


@pytest.fixture
def usar_rotas():
    from app.tools import transporte

    def trocar(t):
        app.dependency_overrides[transporte] = lambda: t
        return t

    yield trocar
    app.dependency_overrides.pop(transporte, None)


@pytest.fixture
def limiar(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "compactacao_limiar", 2_000)
    monkeypatch.setattr(settings, "compactacao_turnos_literais", 2)


@pytest.fixture
def resumidor():
    """Troca o modelo do Resumo. Guarda o texto que ele recebeu em cada chamada."""
    from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, UserPromptPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    from app.compactacao import MODELO_RESUMO, modelo_resumo
    from tests.test_compactacao import RESUMO

    entradas: list[str] = []

    def responder(msgs: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        entradas.append(str([p.content for m in msgs for p in m.parts if isinstance(p, UserPromptPart)]))
        return ModelResponse(parts=[TextPart(RESUMO)])

    app.dependency_overrides[modelo_resumo] = lambda: FunctionModel(responder, model_name=MODELO_RESUMO)
    yield entradas
    app.dependency_overrides.pop(modelo_resumo, None)


@pytest.fixture
def usar_jev():
    from tests.test_roteador import jev_falso

    def trocar(responder):
        app.dependency_overrides[cliente_jev] = lambda: jev_falso(responder)

    yield trocar
    app.dependency_overrides.pop(cliente_jev, None)


@pytest.fixture
def google():
    """O mesmo MockTransport nas rotas do Conector e nas Tools do chat."""
    from app.conectores import transporte_google
    from app.tools import transporte
    from tests.test_conectores import Google

    g = Google()
    app.dependency_overrides[transporte_google] = lambda: g
    app.dependency_overrides[transporte] = lambda: g
    yield g
    app.dependency_overrides.pop(transporte_google, None)
    app.dependency_overrides.pop(transporte, None)


@pytest.fixture(scope="module")
def demo():
    """Sobe o servidor demo com token e devolve a URL do /mcp. Um servidor por módulo."""
    import os
    import socket
    import subprocess
    import sys
    import time

    from tests.test_mcp import SERVIDOR, TOKEN, porta_livre

    porta = porta_livre()
    env = {**os.environ, "PORT": str(porta), "MCP_DEMO_TOKEN": TOKEN}
    proc = subprocess.Popen([sys.executable, str(SERVIDOR)], env=env)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", porta), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("servidor demo não subiu")
        yield f"http://127.0.0.1:{porta}/mcp"
    finally:
        proc.terminate()
        proc.wait(5)
