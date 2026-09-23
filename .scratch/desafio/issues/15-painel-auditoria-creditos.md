# 15 — Painel de auditoria e créditos

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 08, 13
**Refs:** ADR 0004, 0007.

**What to build:** `GET /api/audit` com filtros (usuário, conversa, tipo, período, paginação). Tela "Auditoria" com tabela e detalhe do payload. Tela "Créditos": saldo, cap, gasto por dia e por modelo, últimas linhas do ledger. Usuário comum vê o próprio. Conta demo com flag admin vê tudo e o cap global.

**Aceite:**
- [~] Um fluxo completo (login → mensagem com tool → compactação → share) aparece em ordem na auditoria. Sem a compactação: o 12 não estava commitado.
- [x] Saldo exibido = cap − soma do ledger, verificado em teste.

## Answer
- `GET /api/audit` (usuário, conversa, tipo, período, `limit`/`offset`), `GET /api/audit/tipos`, `GET /api/credits/{me,global}/painel?tz=` (saldo, gasto por dia no fuso do browser, por modelo, últimas 20 do Ledger), `GET /api/admin/usuarios`. Sem migração.
- Conta demo vira `is_superuser` no startup. Comum vê só o próprio; admin vê tudo, o global e `/admin`.
- Front: `/auditoria` (filtros na URL, paginação, drawer do payload), `/creditos` (saldo, barra do Cap, 2 gráficos recharts, Ledger), `/admin`. 8/8 pytest; 12 screenshots `15-*.png` no Brave dark.
- Ressalva: o aceite do fluxo cobre login → tool → share. A compactação (12) ainda não estava commitada; o 12 deve pôr o passo `compaction` em `test_fluxo_aparece_em_ordem`.
- REVISAR(human): `_escopo` (quem vê o quê), `_painel` (dia no fuso), `garantir_conta_demo` (flag admin).
