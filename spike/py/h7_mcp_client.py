"""H7: MCPToolset do Pydantic AI conecta no GitHub MCP remoto e no servidor local; lista tools e a era."""
import asyncio, os
from dotenv import load_dotenv
from pydantic_ai.mcp import MCPToolset

load_dotenv("../../.env")

async def probe(nome, toolset, call=None):
    print(f"== {nome} ==")
    try:
        async with toolset:
            ir = toolset.client.initialize_result
            era = "legada (handshake initialize)" if ir is not None else "moderna (sem initialize, stateless)"
            print("era da sessao:", era)
            if ir is not None:
                print("protocolVersion negociada:", getattr(ir, "protocol_version", None) or getattr(ir, "protocolVersion", None))
            try: print("server_info:", toolset.server_info)
            except Exception as e: print("server_info: indisponivel", e)
            tools = await toolset.list_tools()
            print(f"tools ({len(tools)}):", sorted(t.name for t in tools))
            if call:
                r = await toolset.direct_call_tool(*call)
                print("call", call, "->", r)
    except Exception as e:
        print("ERRO:", type(e).__name__, e)

async def main():
    await probe("local mcp 2.x", MCPToolset("http://127.0.0.1:8765/mcp"), call=("somar", {"a": 2, "b": 3}))
    await probe("GitHub remoto", MCPToolset("https://api.githubcopilot.com/mcp/", headers={"Authorization": f"Bearer {os.environ['GITHUB_PAT']}"}))

asyncio.run(main())
