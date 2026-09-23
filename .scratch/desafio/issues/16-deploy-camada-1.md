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

**Contexto do VPS (23/09, noite):** conta OCI nova falhou. Deploy temporário no VPS Always Free do trabalho do Toneli, que já roda outro projeto. Chaves SSH chegam dia 24 de manhã. Antes de qualquer alteração: inventariar o que roda (`docker ps`, `ss -tlnp`, proxy existente em 80/443). Nunca parar nem alterar serviço existente. Se houver proxy, adicionar o host `chat.toneli.dev.br` nele. Se não houver, subir o Caddy nosso. Tudo do nosso lado em um único `docker compose` em `/opt/tess-chat`, removível com `down -v`.
