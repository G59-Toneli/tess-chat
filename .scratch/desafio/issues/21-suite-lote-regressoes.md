# 21 — Suíte completa em lote e regressões conhecidas

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 09b, 20

**What to build:** rodar `cd api && uv run pytest` e `cd web && npm run build && npx tsc --noEmit`. Corrigir toda regressão com diff mínimo. Não refatorar.

**Regressões já conhecidas (reportadas pelos agentes):**
- `api/tests/test_roteador.py::test_anexo_vai_no_state` quebra desde o 09: URL `data:` recusada. Decidir se o teste ou o código está errado, olhando o ADR do Roteador e o do anexo.
- `/tools` (07b/07c) mostra o switch de toggle global para não-admin; desde o 14 o `PUT /api/tools/{nome}` exige superuser e o usuário recebe 403 com toast. Esconder ou desabilitar o switch quando o usuário não é superuser (o front já sabe quem é admin: ver `Admin.tsx`).

**Aceite:**
- [ ] `uv run pytest` verde (exceto testes que dependem de chave real e são pulados por design).
- [ ] `npm run build` e `tsc` limpos.
- [ ] Não-admin em `/tools` não vê switch ativo.
