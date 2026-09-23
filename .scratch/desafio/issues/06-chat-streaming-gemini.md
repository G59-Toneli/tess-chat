# 06 — Chat com streaming via Pydantic AI + Gemini, persistindo tudo

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 05
**Refs:** ADR 0001, 0003. Resultado do spike (hipóteses 2, 4, 5).

**What to build:** `POST /api/chat/{conversation_id}` que carrega o histórico do banco, roda o Agent com `gemini-3.8-flash`, streama via `VercelAIAdapter`, e ao fim persiste a mensagem do assistente com `RunUsage` (entrada, saída, thinking, cache). Evento `llm_call` com tokens, modelo, latência.

**Aceite:**
- [ ] Segunda mensagem na mesma conversa vê a primeira (histórico do banco).
- [ ] Tokens gravados na mensagem batem com o `usage_metadata` do provedor (teste com resposta gravada).
- [ ] Erro do provedor vira evento `llm_error` e resposta 502 legível.

**Do spike:** `result.usage` é propriedade. `RunUsage.output_tokens` já inclui thinking; thinking à parte em `details["thoughts_tokens"]`; cache em `cache_read_tokens`. Configurar nível de thinking explicitamente (default deu ~7 s até o primeiro token).
