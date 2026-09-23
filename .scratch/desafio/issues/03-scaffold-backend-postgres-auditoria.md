# 03 — Scaffold do backend, Postgres, migrações e auditoria

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 01
**Refs:** ADR 0001, 0007. `CONTEXT.md`.

**What to build:** projeto `api/` com uv, FastAPI, SQLAlchemy async, Alembic, pytest. Compose local com Postgres. Tabela `audit_events` com `REVOKE UPDATE, DELETE` para o usuário da app. Helper `audit(event_type, **payload)`. Endpoint `/health`.

**Aceite:**
- [x] `docker compose up` + `alembic upgrade head` sobem limpos.
- [x] Teste: inserir evento e tentar `UPDATE`/`DELETE` como usuário da app falha com erro de permissão.
- [x] `/health` responde 200.
- [x] `pytest` verde.

**Do spike:** Python 3.14 funciona. `asyncpg` entra como dependência explícita. Postgres do compose local na porta 5433 para não colidir.
