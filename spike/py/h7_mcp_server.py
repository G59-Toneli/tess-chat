"""H7: servidor MCP minimo com mcp 2.x em Streamable HTTP (porta 8765, path /mcp)."""
from mcp.server.mcpserver import MCPServer

server = MCPServer("spike-local")

@server.tool()
def somar(a: int, b: int) -> int:
    """Soma dois inteiros."""
    return a + b

@server.tool()
def eco(texto: str) -> str:
    """Devolve o texto recebido."""
    return texto

if __name__ == "__main__":
    server.run("streamable-http", host="127.0.0.1", port=8765)
