# 17 — Cliente MCP: usuário cadastra servidor e usa as tools dele

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** nenhum (era 16; liberado em 23/09 para rodar em localhost, deploy só troca a URL)
**Refs:** ADR 0009. Spike hipótese 7. Camada 2.

**What to build:** tabela `mcp_servers` (usuário, nome, url, header de auth criptografado, ativo). Ao cadastrar: conecta, lista tools, grava no registro com origem `mcp`. Toggle por conversa igual às nativas. Chamada via cliente dual-era. Evento `mcp_server_added`, `tool_call` com origem. Front: tela "Servidores MCP" e tools MCP aparecem no painel da conversa.

**Aceite:**
- [x] Cadastrar o servidor remoto do GitHub com PAT e perguntar "quais meus repos" gera tool_call MCP e resposta correta.
- [x] Servidor fora do ar no cadastro devolve erro legível, sem gravar.
- [x] Servidor mínimo próprio em `deploy/mcp-demo/` sobe no compose e funciona como plano B.

**Do spike:** `MCPToolset` confirmado com GitHub remoto (45 tools) e servidor `mcp` 2.x local. Só era moderna exercitada. Servidor de demo usa `MCPServer` do SDK, não `FastMCP`.

## Answer
Tabela `mcp_servers` (migração 0013), `api/app/mcp.py` (cadastro, toggle, remoção) e tools MCP no registro com `mcp_server_id`, filtradas pelo dono em `estado_da_conversa`. No turno, `MCPToolset` prefixado e filtrado pelas tools ativas, dentro da `Auditada`; `tool_call` leva `origem`. Header cifrado com o Fernet do 18. Front: tela `/mcp` e badge "mcp" no SeletorTools. Demo em `deploy/mcp-demo/` e serviço `mcp-demo` no compose (porta 8765).
Aceite 1 real: GitHub com o PAT do .env (funcionou, sem 401), "quais meus repos?" chamou `get_me` e `search_repositories` e listou os 31 repos. Nesse turno só as duas estavam ligadas. Turno extra com as 45 tools do GitHub ligadas (estado padrão) respondeu 200: o Gemini aceita as 45 declarations.
Ressalvas: servidor MCP que cai depois derruba o turno das Conversas do dono; URL livre permite SSRF. Ambas em DECISOES-AUTONOMAS.
