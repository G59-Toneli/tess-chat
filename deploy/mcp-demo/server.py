"""Servidor MCP mínimo (plano B do ticket 17). mcp 2.x, MCPServer, Streamable HTTP em /mcp.

Env: HOST (padrão 127.0.0.1), PORT (padrão 8765), MCP_DEMO_TOKEN (opcional: exige Authorization: Bearer <token>).
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

server = MCPServer("tess-mcp-demo")


@server.tool()
def somar(a: float, b: float) -> float:
    """Soma dois números."""
    return a + b


@server.tool()
def hora_atual(fuso: str = "America/Sao_Paulo") -> str:
    """Data e hora atuais no fuso IANA informado (ex.: America/Sao_Paulo)."""
    return datetime.now(ZoneInfo(fuso)).isoformat(timespec="seconds")


def app(token: str | None):
    """App ASGI. Com token, recusa 401 quem não manda o Bearer certo."""
    # Sem proteção de DNS rebinding: no compose o Host é o nome do serviço, não localhost.
    mcp_app = server.streamable_http_app(
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)
    )
    if not token:
        return mcp_app

    async def protegido(scope, receive, send):
        if scope["type"] == "http" and dict(scope["headers"]).get(b"authorization") != f"Bearer {token}".encode():
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"token invalido"})
            return
        await mcp_app(scope, receive, send)

    return protegido


if __name__ == "__main__":
    uvicorn.run(
        app(os.environ.get("MCP_DEMO_TOKEN")),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8765")),
        log_level="warning",
    )
