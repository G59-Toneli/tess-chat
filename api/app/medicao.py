"""Custo fixo por chamada: ordem estável das tools e hash do prefixo de cada request (ticket 58)."""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import ToolDefinition
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit


def hash_prefixo(instrucoes: list[str], tools: list[ToolDefinition]) -> str:
    """sha256 curto das instructions e das tool defs, na ordem em que vão ao modelo."""
    corpo = {
        "instrucoes": instrucoes,
        "tools": [[t.name, t.description, t.parameters_json_schema] for t in tools],
    }
    texto = json.dumps(corpo, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


@dataclass
class Medidor(AbstractCapability[Any]):
    """Ordena as tools por nome e anota, antes de cada request, o hash do prefixo e quantas tools foram.

    O cache implícito do Gemini casa por prefixo. A ordem das tools vinha do banco sem ORDER BY
    e do list_tools de cada servidor MCP; ordenar aqui estabiliza sem mudar o conjunto.
    """

    # O Pydantic AI copia a capability por run: o estado mora num objeto compartilhado.
    pedidos: list[dict[str, Any]] = field(default_factory=list)

    async def prepare_tools(self, ctx: RunContext[Any], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
        return sorted(tool_defs, key=lambda t: t.name)

    async def before_model_request(
        self, ctx: RunContext[Any], request_context: ModelRequestContext
    ) -> ModelRequestContext:
        p = request_context.model_request_parameters
        instrucoes = [i.content for i in p.instruction_parts or []]
        tools = list(p.function_tools)
        self.pedidos.append({"tools": len(tools), "prefix_hash": hash_prefixo(instrucoes, tools)})
        return request_context


# REVISAR(human): um llm_request por ModelResponse do turno, com o uso daquela chamada.
# O i-ésimo request anotado pelo Medidor casa com a i-ésima ModelResponse: retry e fallback
# do provedor rodam dentro do mesmo request, e request cancelado sem resposta sobra no fim (zip corta).
# Aditivo: não entra no Ledger nem no custo. O llm_call do turno continua sendo o que cobra.
async def auditar_requests(
    s: AsyncSession,
    uid: uuid.UUID,
    cid: uuid.UUID,
    modelo: str,
    novas: list[ModelMessage],
    medidor: Medidor | None,
) -> None:
    respostas = [m for m in novas if isinstance(m, ModelResponse)]
    pedidos = medidor.pedidos if medidor else []
    for i, (r, p) in enumerate(zip(respostas, pedidos)):
        await audit(
            s,
            "llm_request",
            user_id=uid,
            conversation_id=cid,
            model=modelo,
            input_tokens=r.usage.input_tokens,
            output_tokens=r.usage.output_tokens,
            payload={
                "indice": i,
                "cache_read_tokens": r.usage.cache_read_tokens,
                "modelo_real": r.model_name,
                **p,
            },
        )
