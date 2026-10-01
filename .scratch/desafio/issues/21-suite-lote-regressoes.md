# 21 — Suíte completa em lote e regressões conhecidas

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 17, 18 (roda no fim do bloco, depois que o último ticket de código fechar)

**What to build:** rodar `cd api && uv run pytest` e `cd web && npm run build && npx tsc --noEmit`. Corrigir toda regressão com diff mínimo. Não refatorar.

**Regressões já conhecidas (reportadas pelos agentes):**
- `api/tests/test_roteador.py::test_anexo_vai_no_state` quebra desde o 09: URL `data:` recusada. Decidir se o teste ou o código está errado, olhando o ADR do Roteador e o do anexo.
- `/tools` (07b/07c) mostra o switch de toggle global para não-admin; desde o 14 o `PUT /api/tools/{nome}` exige superuser e o usuário recebe 403 com toast. Esconder ou desabilitar o switch quando o usuário não é superuser (o front já sabe quem é admin: ver `Admin.tsx`).

- `/tools` lista as 3 tools do Google (18) com badge "nativa" porque `Tools.tsx` só distingue `mcp`. Mostrar a origem real (`google`, e `mcp` do 17). Ajuste de uma linha.
- O teste do Roteador acima agora falha por outro motivo desde o 09b: anexo inline dá 422. Ajustar o teste para o formato por referência do 09b.

**Aceite:**
- [x] `uv run pytest` verde (exceto testes que dependem de chave real e são pulados por design).
- [x] `npm run build` e `tsc` limpos.
- [x] Não-admin em `/tools` não vê switch ativo.

## Answer
- Suíte api antes 131 passed / 1 failed; depois 132 passed / 0 failed / 0 skipped. `npm run build` e `tsc --noEmit` limpos antes e depois. - `test_anexo_vai_no_state`: o teste estava errado, não o código. O 09/09b só aceita anexo por referência a `/api/attachments` (bloqueia `data:` e URL externa). O teste agora sobe o PDF e manda a referência. - `Tools.tsx`: switch global `disabled` para não-admin (mostra o estado, não alterna) e badge com a origem real (`nativa`, `google`, `MCP`). Screenshot: `.scratch/desafio/screens/21-tools-nao-admin.png`. - Ressalva: o Playwright do MCP roda Chromium, não Brave (`navigator.brave` ausente). Ficou no banco de dev o usuário `naoadmin21@teste.dev`. 0 chamadas Gemini/Tavily/Jev.