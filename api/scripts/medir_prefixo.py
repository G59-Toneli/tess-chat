"""Custo fixo por chamada de um Usuário: tokens do system prompt e das tools de cada servidor (ticket 58).

Monta instructions e tool defs como o turno monta (toolset da Conversa, Medidor, GoogleModel.prepare_request)
e conta com o countTokens do Gemini, sem geração. countTokens não é cobrado.

Uso (produção):
    docker compose exec app python scripts/medir_prefixo.py --email demo@exemplo.com [--conversa UUID] [--seco]

--seco: não chama o Gemini; imprime só hash do prefixo e tamanho em caracteres.
Chamadas ao Gemini: 3 + uma por grupo de tools (nativas, google, cada Servidor MCP).
Efeito colateral: igual ao de um turno. Sonda os Servidores MCP e renova token OAuth vencendo.
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.auth import User  # noqa: E402
from app.chat import _gemini, agent  # noqa: E402
from app.config import settings  # noqa: E402
from app.configuracao import MODELO_PADRAO  # noqa: E402
from app.conversas import Conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.medicao import Medidor  # noqa: E402
from app.tools import ComTeto, toolset_da_conversa  # noqa: E402

URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:countTokens"
CONTEUDO = [{"role": "user", "parts": [{"text": "."}]}]


async def _montar(email: str, conversa: str | None, modelo: str) -> dict[str, Any]:
    """Prefixo do 1º request de um turno: system_instruction, tools no formato do Gemini e o grupo de cada tool."""
    async with SessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == email))
        if user is None:
            sys.exit(f"Usuário não encontrado: {email}")
        if conversa:
            cid = uuid.UUID(conversa)
        else:
            q = select(Conversation.id).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
            cid = await s.scalar(q.limit(1))
            if cid is None:
                sys.exit("Usuário sem Conversa. Passe --conversa.")
        tools = await toolset_da_conversa(s, user.id, cid, None)
        await s.rollback()  # evento de sonda não é gravado: isto é medição, não turno

    visto: dict[str, Any] = {}

    def capturar(msgs: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        visto.update(msgs=msgs, info=info)
        return ModelResponse(parts=[TextPart("ok")])

    medidor = Medidor()
    await agent.run(".", model=FunctionModel(capturar), toolsets=[ComTeto(tools, 1)], capabilities=[medidor])

    # O mesmo caminho do GoogleModel.request: prepare_request transforma os schemas, _build_content_and_config
    # monta system_instruction e tools. Métodos internos do Pydantic AI: conferir ao atualizar a lib.
    gm = _gemini(modelo)
    ajustes, params = gm.prepare_request(None, visto["info"].model_request_parameters)
    _, config = await gm._build_content_and_config(visto["msgs"], ajustes or {}, params)
    grupos: dict[str, str] = {}
    for t in params.function_tools:
        origem = tools.origens.get(t.name, "?")
        grupos[t.name] = f"mcp:{tools.servidores.get(t.name, '?')}" if origem == "mcp" else origem
    return {
        "cid": cid,
        "hash": medidor.pedidos[0]["prefix_hash"],
        "sistema": config.get("system_instruction"),
        "tools": config.get("tools") or [],
        "grupos": grupos,
        "fora_do_ar": tools.fora_do_ar,
    }


def _nome(tool: dict[str, Any]) -> str:
    return tool["function_declarations"][0]["name"]


async def _contar(http: httpx.AsyncClient, modelo: str, sistema: Any, tools: list[Any]) -> int:
    pedido: dict[str, Any] = {"model": f"models/{modelo}", "contents": CONTEUDO}
    if sistema:
        pedido["system_instruction"] = sistema
    if tools:
        pedido["tools"] = tools
    corpo = json.loads(json.dumps({"generate_content_request": pedido}, default=str))
    r = await http.post(URL.format(modelo), json=corpo, headers={"x-goog-api-key": settings.gemini_paid_api_key})
    r.raise_for_status()
    return r.json()["totalTokens"]


def _chars(x: Any) -> int:
    return len(json.dumps(x, ensure_ascii=False, default=str))


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--conversa")
    ap.add_argument("--modelo", default=MODELO_PADRAO)
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args()

    p = await _montar(a.email, a.conversa, a.modelo)
    por_grupo: dict[str, list[Any]] = {}
    for t in p["tools"]:
        por_grupo.setdefault(p["grupos"].get(_nome(t), "?"), []).append(t)

    print(f"conversa {p['cid']}  modelo {a.modelo}  prefix_hash {p['hash']}  tools {len(p['tools'])}")
    if p["fora_do_ar"]:
        print(f"fora do turno (sonda/OAuth): {', '.join(p['fora_do_ar'])}")
    print(f"ordem: {', '.join(_nome(t) for t in p['tools'])}")
    linhas = [("system prompt", _chars(p["sistema"]), None, None)]
    linhas += [(g, _chars(ts), len(ts), ts) for g, ts in sorted(por_grupo.items())]

    if a.seco:
        for nome, chars, n, _ in linhas:
            print(f"{nome:40} {'' if n is None else f'{n:3} tools':10} {chars:>9} chars")
        print(f"{'total':40} {'':10} {sum(c for _, c, _, _ in linhas):>9} chars")
        return

    async with httpx.AsyncClient(timeout=60) as http:
        base = await _contar(http, a.modelo, None, [])
        sistema = await _contar(http, a.modelo, p["sistema"], []) - base
        print(f"{'system prompt':40} {'':10} {sistema:>9} tokens")
        for nome, _, n, ts in linhas[1:]:
            print(f"{nome:40} {f'{n:3} tools':10} {await _contar(http, a.modelo, None, ts) - base:>9} tokens")
        total = await _contar(http, a.modelo, p["sistema"], p["tools"]) - base
        print(f"{'total (prefixo de cada chamada)':40} {'':10} {total:>9} tokens")


if __name__ == "__main__":
    asyncio.run(main())
