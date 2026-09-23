# 16 — Deploy da Camada 1 no VPS com CI

**Type:** task (AFK + HITL)
**Status:** blocked
**Blocked by:** 02, 09, 10, 11, 12, 13, 14, 15
**Refs:** ADR 0011. **Marco: sexta 26/09.**

**What to build:** `deploy/docker-compose.yml` com caddy, app, postgres, volumes persistentes. `.env` no VPS. GitHub Actions: em push na `main`, ssh no VPS, `git pull`, `docker compose up -d --build`, `alembic upgrade head`. Backup diário do Postgres por cron simples.

**HITL:** segredos no GitHub e no VPS.

**Aceite:**
- [ ] Fluxo completo funciona no link público, em janela anônima.
- [ ] Push na main atualiza o VPS sem intervenção.
- [ ] Reiniciar o VPS mantém dados.
