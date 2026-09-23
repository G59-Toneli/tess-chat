# 03 — Scaffold do backend, Postgres, migrações e auditoria

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 01
**Refs:** ADR 0001, 0007. `CONTEXT.md`.

**What to build:** projeto `api/` com uv, FastAPI, SQLAlchemy async, Alembic, pytest. Compose local com Postgres. Tabela `audit_events` com `REVOKE UPDATE, DELETE` para o usuário da app. Helper `audit(event_type, **payload)`. Endpoint `/health`.

**Aceite:**
- [ ] `docker compose up` + `alembic upgrade head` sobem limpos.
- [ ] Teste: inserir evento e tentar `UPDATE`/`DELETE` como usuário da app falha com erro de permissão.
- [ ] `/health` responde 200.
- [ ] `pytest` verde.

**Do spike:** Python 3.14 funciona. `asyncpg` entra como dependência explícita. Postgres do compose local na porta 5433 para não colidir.
