"""Custo fixo por chamada (ticket 58): llm_request por chamada e prefixo estável entre turnos.

Golden de regressão do turno Notion: servidor MCP falso com schemas grandes e ordem rotativa.
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelMessage, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

from app.chat import MODELO
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_conversas import criar, usuario
from tests.test_mcp import cadastrar, porta_livre

SERVIDOR = Path(__file__).parent / "fixtures" / "mcp_grande.py"
# Sequência do turno Notion: busca, lê, atualiza, depois responde.
PASSOS = ["search", "fetch", "update_page"]
ENTRADA = {"entrada": {"id": "p1", "titulo": "t", "conteudo": "c", "propriedades": []}}


@pytest.fixture(scope="module")
def grande():
    porta = porta_livre()
    proc = subprocess.Popen([sys.executable, str(SERVIDOR)], env={**os.environ, "PORT": str(porta)})
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", porta), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("servidor mcp_grande não subiu")
        yield f"http://127.0.0.1:{porta}/mcp"
    finally:
        proc.terminate()
        proc.wait(5)


def modelo_notion(vistos: list[AgentInfo]) -> FunctionModel:
    """Chama as tools de PASSOS em sequência na 1ª pergunta. Na 2ª responde direto."""

    async def stream(msgs: list[ModelMessage], info: AgentInfo):
        vistos.append(info)
        feitos = sum(1 for m in msgs for p in m.parts if isinstance(p, ToolReturnPart))
        primeira = sum(1 for m in msgs for p in m.parts if getattr(p, "part_kind", "") == "user-prompt") == 1
        if primeira and feitos < len(PASSOS):
            nomes = [t.name for t in info.function_tools]
            alvo = next(n for n in nomes if n.startswith("notion_") and n.endswith(f"_{PASSOS[feitos]}"))
            yield {0: DeltaToolCall(name=alvo, json_args=json.dumps(ENTRADA), tool_call_id=f"c{feitos}")}
            return
        yield "Pronto."

    return FunctionModel(stream_function=stream, model_name=MODELO)


async def test_turno_notion_e_o_seguinte_mandam_o_mesmo_prefixo(client, grande, usar_modelo):
    uid, h = await usuario(client)
    srv = (await cadastrar(client, h, grande, nome="notion", autorizacao=None)).json()
    vistos: list[AgentInfo] = []
    usar_modelo(modelo_notion(vistos))
    cid = (await criar(client, h))["id"]

    r1 = await client.post(f"/api/chat/{cid}", json=corpo("atualize a página do projeto"), headers=h)
    r2 = await client.post(f"/api/chat/{cid}", json=corpo("obrigado"), headers=h)

    assert r1.status_code == 200 and r2.status_code == 200
    assert len(vistos) == len(PASSOS) + 2
    ordens = [[t.name for t in info.function_tools] for info in vistos]
    esperadas = {t["nome"] for t in srv["tools"]} | {"web_search", "web_fetch"}
    assert set(ordens[0]) == esperadas
    assert all(o == ordens[0] for o in ordens)
    reqs = await eventos("llm_request", user_id=uid)
    assert len(reqs) == len(vistos)
    assert {e.payload["prefix_hash"] for e in reqs} == {reqs[0].payload["prefix_hash"]}
    assert {e.payload["tools"] for e in reqs} == {len(esperadas)}


async def test_llm_request_soma_o_uso_do_llm_call(client, grande, usar_modelo):
    uid, h = await usuario(client)
    await cadastrar(client, h, grande, nome="notion", autorizacao=None)
    usar_modelo(modelo_notion([]))
    cid = (await criar(client, h))["id"]

    await client.post(f"/api/chat/{cid}", json=corpo("atualize a página do projeto"), headers=h)

    [call] = await eventos("llm_call", user_id=uid)
    reqs = await eventos("llm_request", user_id=uid)
    assert [e.payload["indice"] for e in reqs] == list(range(len(PASSOS) + 1))
    assert sum(e.input_tokens for e in reqs) == call.input_tokens
    assert sum(e.output_tokens for e in reqs) == call.output_tokens
    assert all(e.cost_micro_usd is None for e in reqs)

