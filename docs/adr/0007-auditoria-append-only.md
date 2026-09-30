# ADR 0007 — Auditoria em tabela somente-inserção no Postgres, visível no app

**Status:** aceito, 2026-09-23

## Decisão
Tabela `audit_events` com `ts`, `user_id`, `conversation_id`, `event_type`, `payload jsonb`, tokens, custo, `latency_ms`, `model`. O usuário de banco da aplicação recebe `REVOKE UPDATE, DELETE` nessa tabela. Tela no app com filtro por usuário e conversa. Langfuse e Logfire não entram: o que se avalia é o app, não painel de terceiro, e Langfuse self-hosted pede 16 GB.

## Consequências
- Todo fluxo relevante emite evento: login, mensagem, chamada de modelo, tool, roteador, compactação, share, conector, cap atingido.
- Ledger (ADR 0004) e auditoria são tabelas distintas. Uma é dinheiro. A outra é história.
