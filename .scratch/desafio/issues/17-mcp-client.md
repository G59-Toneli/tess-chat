# 17 — Cliente MCP: usuário cadastra servidor e usa as tools dele

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** nenhum (era 16; liberado em 23/09 para rodar em localhost, deploy só troca a URL)
**Refs:** ADR 0009. Spike hipótese 7. Camada 2.

**What to build:** tabela `mcp_servers` (usuário, nome, url, header de auth criptografado, ativo). Ao cadastrar: conecta, lista tools, grava no registro com origem `mcp`. Toggle por conversa igual às nativas. Chamada via cliente dual-era. Evento `mcp_server_added`, `tool_call` com origem. Front: tela "Servidores MCP" e tools MCP aparecem no painel da conversa.

**Aceite:**
- [ ] Cadastrar o servidor remoto do GitHub com PAT e perguntar "quais meus repos" gera tool_call MCP e resposta correta.
- [ ] Servidor fora do ar no cadastro devolve erro legível, sem gravar.
- [ ] Servidor mínimo próprio em `deploy/mcp-demo/` sobe no compose e funciona como plano B.

**Do spike:** `MCPToolset` confirmado com GitHub remoto (45 tools) e servidor `mcp` 2.x local. Só era moderna exercitada. Servidor de demo usa `MCPServer` do SDK, não `FastMCP`.
