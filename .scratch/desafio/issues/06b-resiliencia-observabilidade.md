# 06b — Retry, fallback de modelo e observabilidade do turno

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 10
**Refs:** ADR 0012, 0003, 0004, 0007.

**What to build:** em `api/app/chat.py`: `FallbackModel` com a ordem do ADR 0012; retry com backoff e jitter (3 tentativas) só em erro transitório; eventos `llm_retry`, `llm_fallback`; `llm_call` enriquecido com modelo pedido vs. respondido, latência até o primeiro token, latência total, motivo de término, tentativas. O modelo respondido vai na Mensagem e no Ledger com o preço dele. Se houver `OPENAI_API_KEY` no `.env`, cadastrar preço do modelo OpenAI escolhido na `price_table` (migração de dados) e incluí-lo no fallback; senão, só os dois Gemini. Front: enquanto há retry, o indicador de "pensando" vira "tentando de novo (2/3)". Não altere o comportamento do roteador (ticket 11) nem das tools (ticket 10).

**Aceite:**
- [x] Teste com `FunctionModel` que falha 2 vezes com 503 e responde na 3ª: resposta chega, 2 eventos `llm_retry`, 1 `llm_call` com `tentativas=3`.
- [x] Teste em que o primeiro modelo falha sempre: o segundo responde, evento `llm_fallback`, Mensagem e Ledger gravam o segundo modelo e o preço dele.
- [x] Erro 400 não gera retry.
- [x] `llm_call` traz latência até o primeiro token e total.

**Adendo (do ticket 10):** incluir `UsageLimits(tool_calls_limit=...)` por turno (default 5, vindo de Configuração quando o 14 existir) e evento `tool_limit_reached`. Um turno gerou 4 buscas Tavily seguidas; sem teto, o free tier evapora.

## Answer
`app/resiliencia.py`: `ComRetry` (tenacity, 3 tentativas, backoff exponencial com jitter ou Retry-After) em volta de cada modelo, `FallbackModel` 3.8 → 3.7 com a mesma regra de transitório. `chat.py` grava `llm_retry`, `llm_fallback`, `tool_limit_reached` e `llm_call` com modelo pedido/respondido, TTFT, total, motivo de término e tentativas; Mensagem e Ledger levam o modelo que respondeu. `UsageLimits(tool_calls_limit=5)` via `settings`.
Ressalvas: migração de dados `0010` com preço do 3.7 (INFERIDO = 3.8), sem OpenAI (sem chave). Front sem "tentando de novo": o retry acontece antes da resposta HTTP abrir. Turno cortado pelo teto não é cobrado. Detalhes em DECISOES-AUTONOMAS.
