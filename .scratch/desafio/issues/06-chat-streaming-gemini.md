# 06 — Chat com streaming via Pydantic AI + Gemini, persistindo tudo

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 05
**Refs:** ADR 0001, 0003. Resultado do spike (hipóteses 2, 4, 5).

**What to build:** `POST /api/chat/{conversation_id}` que carrega o histórico do banco, roda o Agent com `gemini-3.8-flash`, streama via `VercelAIAdapter`, e ao fim persiste a mensagem do assistente com `RunUsage` (entrada, saída, thinking, cache). Evento `llm_call` com tokens, modelo, latência.

**Aceite:**
- [x] Segunda mensagem na mesma conversa vê a primeira (histórico do banco).
- [x] Tokens gravados na mensagem batem com o `usage_metadata` do provedor (teste com resposta gravada).
- [x] Erro do provedor vira evento `llm_error` e resposta 502 legível.

**Do spike:** `result.usage` é propriedade. `RunUsage.output_tokens` já inclui thinking; thinking à parte em `details["thoughts_tokens"]`; cache em `cache_read_tokens`. Configurar nível de thinking explicitamente (default deu ~7 s até o primeiro token).

## Answer
- `POST /api/chat/{conversation_id}` em `api/app/chat.py`: histórico do banco, `gemini-3.8-flash` com `thinking_level=low`, stream via `VercelAIAdapter` (sdk 7). Do body do front só vale a última mensagem, que precisa ser do usuário.
- Usuário e assistente gravados juntos no fim do turno, em partes do AI SDK. Mensagem do assistente com input/output/thinking/cache do `RunUsage` (migração 0004). Eventos `message_sent` e `llm_call`.
- Erro do provedor antes do primeiro evento: `llm_error` e 502 com `detail`. Erro no meio do stream: `llm_error` e chunk de erro no stream (o 200 já saiu).
- Ressalva: a resposta gravada (`tests/fixtures/gemini_stream.sse`) veio sem thoughts, então o teste de tokens não exercita thinking > 0. Verificação manual (local, uvicorn 127.0.0.1:8765, Postgres 5433): primeiro token em 1,8 s e 0,9 s, segunda mensagem viu a primeira.
- `REVISAR(human)`: `_persistir` (gravação conjunta no fim) e `chat` (502 só antes do primeiro evento).
