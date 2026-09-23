# api

Backend FastAPI. Os testes são de integração e rodam contra o Postgres do compose (porta 5433).

Pré-requisito: `.env` na raiz do projeto com `DATABASE_URL` (tess_app) e `DATABASE_URL_OWNER` (tess_owner).

Rodar os testes, a partir da raiz do projeto:

```sh
docker compose up -d --wait
(cd api && uv run alembic upgrade head)
(cd api && uv run pytest)
```

Subir a API: `cd api && uv run uvicorn app.main:app --reload`.
