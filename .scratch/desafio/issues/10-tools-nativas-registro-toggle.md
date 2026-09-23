# 10 — Registro de Tools nativas: web_search e web_fetch com toggle por conversa

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 06
**Refs:** ADR 0009.

**What to build:** tabela `tools` (nome, origem, descrição, schema, ativa_global), `conversation_tools` (toggle). Tools nativas `web_search` (Tavily) e `web_fetch` (Jina Reader com fallback trafilatura). O Agent recebe só as tools ativas da conversa. Evento `tool_call` com nome, args, duração, tamanho do resultado. Front: painel de tools na conversa com switches.

**Aceite:**
- [ ] Com `web_search` desligada, pergunta "notícias de hoje" não gera tool_call.
- [ ] Com ligada, gera evento `tool_call` e a resposta cita a fonte.
- [ ] `web_fetch` de uma URL devolve texto limpo.

**Chave:** `TAVILY_API_KEY` no `.env` está no plano free (1.000 créditos/mês). Nos testes use resposta gravada. Chamada real só na verificação manual final, no máximo 5.
