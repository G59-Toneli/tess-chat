# 06b — Retry, fallback de modelo e observabilidade do turno

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 10
**Refs:** ADR 0012, 0003, 0004, 0007.

**What to build:** em `api/app/chat.py`: `FallbackModel` com a ordem do ADR 0012; retry com backoff e jitter (3 tentativas) só em erro transitório; eventos `llm_retry`, `llm_fallback`; `llm_call` enriquecido com modelo pedido vs. respondido, latência até o primeiro token, latência total, motivo de término, tentativas. O modelo respondido vai na Mensagem e no Ledger com o preço dele. Se houver `OPENAI_API_KEY` no `.env`, cadastrar preço do modelo OpenAI escolhido na `price_table` (migração de dados) e incluí-lo no fallback; senão, só os dois Gemini. Front: enquanto há retry, o indicador de "pensando" vira "tentando de novo (2/3)". Não altere o comportamento do roteador (ticket 11) nem das tools (ticket 10).

**Aceite:**
- [ ] Teste com `FunctionModel` que falha 2 vezes com 503 e responde na 3ª: resposta chega, 2 eventos `llm_retry`, 1 `llm_call` com `tentativas=3`.
- [ ] Teste em que o primeiro modelo falha sempre: o segundo responde, evento `llm_fallback`, Mensagem e Ledger gravam o segundo modelo e o preço dele.
- [ ] Erro 400 não gera retry.
- [ ] `llm_call` traz latência até o primeiro token e total.
