# 24 — ESTRUTURA.md e MOTIVACOES.md atualizados com 17, 18, 21, 23

**Type:** task (AFK, só docs)
**Status:** resolved
**Blocked by:** 19
**Refs:** `docs/ESTRUTURA.md`, `docs/MOTIVACOES.md`, tickets 17, 18, 21, 23, `docs/DECISOES-AUTONOMAS.md`.

**Problema (achado do 19):** `ESTRUTURA.md` foi escrito antes do 17 e do 18 e descreve MCP e Conector como inexistentes. `MOTIVACOES.md` não cobre as decisões novas em `DECISOES-AUTONOMAS.md` (httpx no lugar da lib do Google, Fernet para tokens e headers, RLS na tabela de tools MCP, prefixo de tool por usuário, state JWT no OAuth).

**What to build:** atualizar os dois docs. Em `ESTRUTURA.md`: `api/app/mcp.py`, `api/app/conectores.py`, migrações 0012 e 0013, `deploy/mcp-demo/`, telas `/mcp`, `/conectores`, `/config`, `.env.example`, tickets 20 a 24 no mapa. Em `MOTIVACOES.md`: uma entrada curta por decisão nova, linkando a linha de `DECISOES-AUTONOMAS.md`. Se o 23 já tiver fechado quando você rodar, inclua; senão, marque "em andamento (ticket 23)". Nada de código.

**Aceite:**
- [x] `grep -n "inexist\|não existe\|em andamento" docs/ESTRUTURA.md` não cita MCP nem Conector como ausentes.
- [x] Cada decisão de `DECISOES-AUTONOMAS.md` dos tickets 17 e 18 tem um "por quê" em `MOTIVACOES.md`.

## Answer
- `ESTRUTURA.md`: retrato depois do 23 (`fc524ee`). Entraram `mcp.py`, `conectores.py`, migrações 0012 e 0013, `deploy/mcp-demo/`, telas `/mcp` e `/conectores`, `.env.example`, `README.md`, `ENTREVISTA.md`, tabela de tickets 15 a 24 e as marcas `REVISAR(human)` novas.
- Sugestões do 20 marcadas: 1, 2 e 8 resolvidas; 4 em parte.
- `MOTIVACOES.md`: seção 6 com um "por quê" por decisão do 17, 18 e 23, linkando `DECISOES-AUTONOMAS.md`. O 23 fechou antes deste ticket, então entrou como feito.
- Aceite: o grep só acha a sugestão 4 (`spike/out/`, Caddyfile, CI). Nenhuma linha cita MCP ou Conector como ausente.
- Ressalva: o glossário ainda diz origem `nativa` ou `mcp`; a origem `google` está só no MOTIVACOES. Nada novo em `REVISAR(human)`.
