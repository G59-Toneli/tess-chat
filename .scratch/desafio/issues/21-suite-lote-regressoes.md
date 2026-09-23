# 21 — Suíte completa em lote e regressões conhecidas

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 17, 18 (roda no fim do bloco, depois que o último ticket de código fechar)

**What to build:** rodar `cd api && uv run pytest` e `cd web && npm run build && npx tsc --noEmit`. Corrigir toda regressão com diff mínimo. Não refatorar.

**Regressões já conhecidas (reportadas pelos agentes):**
- `api/tests/test_roteador.py::test_anexo_vai_no_state` quebra desde o 09: URL `data:` recusada. Decidir se o teste ou o código está errado, olhando o ADR do Roteador e o do anexo.
- `/tools` (07b/07c) mostra o switch de toggle global para não-admin; desde o 14 o `PUT /api/tools/{nome}` exige superuser e o usuário recebe 403 com toast. Esconder ou desabilitar o switch quando o usuário não é superuser (o front já sabe quem é admin: ver `Admin.tsx`).

- `/tools` lista as 3 tools do Google (18) com badge "nativa" porque `Tools.tsx` só distingue `mcp`. Mostrar a origem real (`google`, e `mcp` do 17). Ajuste de uma linha.
- O teste do Roteador acima agora falha por outro motivo desde o 09b: anexo inline dá 422. Ajustar o teste para o formato por referência do 09b.

**Aceite:**
- [ ] `uv run pytest` verde (exceto testes que dependem de chave real e são pulados por design).
- [ ] `npm run build` e `tsc` limpos.
- [ ] Não-admin em `/tools` não vê switch ativo.
