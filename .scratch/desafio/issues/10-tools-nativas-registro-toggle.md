# 10 — Registro de Tools nativas: web_search e web_fetch com toggle por conversa

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 06
**Refs:** ADR 0009.

**What to build:** tabela `tools` (nome, origem, descrição, schema, ativa_global), `conversation_tools` (toggle). Tools nativas `web_search` (Tavily) e `web_fetch` (Jina Reader com fallback trafilatura). O Agent recebe só as tools ativas da conversa. Evento `tool_call` com nome, args, duração, tamanho do resultado. Front: painel de tools na conversa com switches.

**Aceite:**
- [x] Com `web_search` desligada, pergunta "notícias de hoje" não gera tool_call.
- [x] Com ligada, gera evento `tool_call` e a resposta cita a fonte.
- [x] `web_fetch` de uma URL devolve texto limpo.

**Chave:** `TAVILY_API_KEY` no `.env` está no plano free (1.000 créditos/mês). Nos testes use resposta gravada. Chamada real só na verificação manual final, no máximo 5.

## Answer
Tabelas `tools` e `conversation_tools` (migração 0006), `app/tools.py` com `web_search` (Tavily), `web_fetch` (Jina + fallback trafilatura), toolset por Conversa com `tool_call` auditado e API `GET /api/tools`, `GET/PUT /api/conversations/{id}/tools` (`tool_toggled`). Front do painel não feito: fica para o 07/tela de tools.
Testes: 9/9 em `test_tools.py` com HTTP gravado; `test_chat` e `test_credito` seguem verdes. Manual: com Gemini real, "notícias de hoje" gerou `tool_call` e resposta citando g1/CNN/R7; `web_fetch` real devolve texto sem HTML. Desligada verificada só no teste (modelo recebe zero tools).
Ressalva: o Gemini fez 4 buscas num turno (5 requests). Sem teto de tool calls por turno, um turno pode gastar vários créditos Tavily. Créditos Tavily usados: 5.
REVISAR(human): `web_fetch` (ordem Jina → trafilatura, corte) e `estado_da_conversa` (regra de herança do toggle).
