"""Servidor MCP falso com schemas grandes, no formato de um servidor tipo Notion (ticket 58).

Cada list_tools devolve as tools numa rotação diferente: simula servidor sem ordem garantida.
Env: PORT.
"""

import os
from typing import Any

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

NOMES = [
    "search", "fetch", "create_pages", "update_page", "move_pages", "duplicate_page",
    "create_database", "update_database", "create_comment", "get_comments", "get_users", "get_teams",
]
TEXTO = (
    "Descrição longa no estilo dos servidores MCP de produtividade. Explica quando usar a ferramenta, "
    "quais campos são obrigatórios, o formato de cada id e os limites de paginação. "
)


class Propriedade(BaseModel):
    nome: str = Field(description=TEXTO)
    tipo: str = Field(description=TEXTO)
    valor: dict[str, Any] = Field(description=TEXTO)


class Entrada(BaseModel):
    id: str = Field(description=TEXTO)
    titulo: str = Field(description=TEXTO)
    conteudo: str = Field(description=TEXTO * 2)
    propriedades: list[Propriedade] = Field(description=TEXTO)
    cursor: str | None = Field(default=None, description=TEXTO)


class Rotativo(MCPServer):
    chamadas = 0

    async def list_tools(self):
        tools = await super().list_tools()
        k = Rotativo.chamadas % len(tools)
        Rotativo.chamadas += 1
        return tools[k:] + tools[:k]


server = Rotativo("mcp-grande")


def _fn(nome: str):
    def ferramenta(entrada: Entrada) -> str:
        return f"{nome}: ok ({entrada.id})"

    return ferramenta


for n in NOMES:
    server.add_tool(_fn(n), name=n, description=f"{n}. " + TEXTO * 6)


if __name__ == "__main__":
    app = server.streamable_http_app(
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)
    )
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["PORT"]), log_level="warning")
