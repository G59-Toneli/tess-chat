# 24 — ESTRUTURA.md e MOTIVACOES.md atualizados com 17, 18, 21, 23

**Type:** task (AFK, só docs)
**Status:** ready-for-agent
**Blocked by:** 19
**Refs:** `docs/ESTRUTURA.md`, `docs/MOTIVACOES.md`, tickets 17, 18, 21, 23, `docs/DECISOES-AUTONOMAS.md`.

**Problema (achado do 19):** `ESTRUTURA.md` foi escrito antes do 17 e do 18 e descreve MCP e Conector como inexistentes. `MOTIVACOES.md` não cobre as decisões novas em `DECISOES-AUTONOMAS.md` (httpx no lugar da lib do Google, Fernet para tokens e headers, RLS na tabela de tools MCP, prefixo de tool por usuário, state JWT no OAuth).

**What to build:** atualizar os dois docs. Em `ESTRUTURA.md`: `api/app/mcp.py`, `api/app/conectores.py`, migrações 0012 e 0013, `deploy/mcp-demo/`, telas `/mcp`, `/conectores`, `/config`, `.env.example`, tickets 20 a 24 no mapa. Em `MOTIVACOES.md`: uma entrada curta por decisão nova, linkando a linha de `DECISOES-AUTONOMAS.md`. Se o 23 já tiver fechado quando você rodar, inclua; senão, marque "em andamento (ticket 23)". Nada de código.

**Aceite:**
- [ ] `grep -n "inexist\|não existe\|em andamento" docs/ESTRUTURA.md` não cita MCP nem Conector como ausentes.
- [ ] Cada decisão de `DECISOES-AUTONOMAS.md` dos tickets 17 e 18 tem um "por quê" em `MOTIVACOES.md`.
