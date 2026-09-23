# 15 — Painel de auditoria e créditos

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 08, 13
**Refs:** ADR 0004, 0007.

**What to build:** `GET /api/audit` com filtros (usuário, conversa, tipo, período, paginação). Tela "Auditoria" com tabela e detalhe do payload. Tela "Créditos": saldo, cap, gasto por dia e por modelo, últimas linhas do ledger. Usuário comum vê o próprio. Conta demo com flag admin vê tudo e o cap global.

**Aceite:**
- [ ] Um fluxo completo (login → mensagem com tool → compactação → share) aparece em ordem na auditoria.
- [ ] Saldo exibido = cap − soma do ledger, verificado em teste.
