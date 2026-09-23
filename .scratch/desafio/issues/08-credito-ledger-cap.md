# 08 — Crédito: Tabela de Preço, Ledger, reserva/acerto, cap duplo

**Type:** task (AFK + HITL)
**Status:** blocked
**Blocked by:** 06
**Refs:** ADR 0004. Spike hipóteses 4 e 5.

**What to build:** tabelas `price_table` (modelo, preço in/out/cache/thinking por 1M em micro-USD, vigente_desde), `credit_ledger` (append-only, uma linha por chamada), `caps` (global e por usuário, em micro-USD). Fluxo reserva → chamada → acerto. Recusa com 402 e evento `cap_reached` quando a reserva estoura. Endpoint `GET /api/credits/me` e `/api/credits/global`.

**HITL:** a função `debit(usage, price) -> int` fica com `TODO(human)`. O agente escreve os testes dela primeiro e para.

**Aceite:**
- [ ] Teste: soma do ledger de uma conversa = soma dos `usage_metadata` gravados × preço vigente.
- [ ] Teste: com cap de 1 micro-USD, a chamada é recusada antes de chegar ao provedor (provedor mockado não é chamado).
- [ ] Teste: mudança de preço com nova vigência não altera linhas antigas.
