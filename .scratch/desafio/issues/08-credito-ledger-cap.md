# 08 — Crédito: Tabela de Preço, Ledger, reserva/acerto, cap duplo

**Type:** task (AFK + HITL)
**Status:** resolved
**Blocked by:** 06
**Refs:** ADR 0004. Spike hipóteses 4 e 5.

**What to build:** tabelas `price_table` (modelo, preço in/out/cache/thinking por 1M em micro-USD, vigente_desde), `credit_ledger` (append-only, uma linha por chamada), `caps` (global e por usuário, em micro-USD). Fluxo reserva → chamada → acerto. Recusa com 402 e evento `cap_reached` quando a reserva estoura. Endpoint `GET /api/credits/me` e `/api/credits/global`.

O agente escreve os testes dela primeiro e para.

**Aceite:**
- [x] Teste: soma do ledger de uma conversa = soma dos `usage_metadata` gravados × preço vigente.
- [x] Teste: com cap de 1 micro-USD, a chamada é recusada antes de chegar ao provedor (provedor mockado não é chamado).
- [x] Teste: mudança de preço com nova vigência não altera linhas antigas.

**Do spike:** usage do stream é cumulativo em todo chunk: gravar o último, nunca somar. Output cobrado = candidates + thoughts; se usar `RunUsage.output_tokens`, não somar `thoughts_tokens` de novo. Reserva via `UsageLimits(count_tokens_before_request=True)`: funciona, custa um `countTokens` extra por request.

## Answer
Migração 0005 com `price_table` (seed Gemini 3.8 Flash, 3.1 Flash-Lite, Jev), `credit_ledger` somente-inserção e `caps`. `app/credito.py`: `debit`, reserva antes da chamada (402 + `cap_reached`), acerto no mesmo commit das Mensagens, `GET /api/credits/me` e `/global`. `llm_call` agora grava `cost_micro_usd`.
Ressalvas: reserva estima o input localmente (~3 chars/token, INFERIDO), sem countTokens; duas chamadas simultâneas podem passar juntas do Cap; preço de 2027-01-01 não semeado.
