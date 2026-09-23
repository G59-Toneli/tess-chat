# ADR 0012 — Retry com backoff e fallback de modelo, tudo auditado

**Status:** aceito, 2026-09-23

## Contexto
Gemini tem instabilidade conhecida (429, 503, timeouts). Um turno que falha sem retry quebra a demo. Toneli também quer observabilidade de agente no banco: qual tool foi escolhida e por quê, quanto custou, o que falhou.

## Decisão
1. **Retry:** até 3 tentativas com backoff exponencial e jitter em erros transitórios (429, 500, 502, 503, 504, timeout). Erros 4xx de request não repetem.
2. **Fallback de modelo:** `FallbackModel` do Pydantic AI. Ordem: `gemini-3.8-flash` → `gemini-3.7-flash` → OpenAI (`gpt-4.1-mini` ou equivalente) se `OPENAI_API_KEY` existir. O modelo que respondeu fica gravado na Mensagem e no Ledger, com o preço dele.
3. **Observabilidade no banco, via `audit_events`:** todo turno emite `llm_call` com modelo pedido, modelo que respondeu, tokens (entrada, saída, thinking, cache), latência até o primeiro token e total, motivo de término, número de tentativas. `llm_retry` por tentativa com o erro. `llm_fallback` quando troca de modelo. `router_decision` com a tool escolhida, a distribuição do Jev e o motivo (confiança acima ou abaixo do limiar). `tool_call` com args, duração, tamanho e erro se houver.

## Consequências
- Fallback para OpenAI exige preço na Tabela de Preço e a chave no ambiente.
- Retry multiplica o tempo até o primeiro token em falha. Front mostra "tentando de novo".
- A tela de auditoria vira o painel de observabilidade do agente. Sem ferramenta externa.
