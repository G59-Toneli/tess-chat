# Decisões autônomas

Decisões fora dos ADRs, tomadas pelo agente executor. Formato: ticket, decisão, alternativa descartada, por quê.

| ticket | decisão | alternativa descartada | por quê |
|---|---|---|---|
| 04 | `JWT_SECRET` e `DEMO_PASSWORD` com default de dev em `app/config.py`. Produção sobrescreve no `.env`. | Exigir a chave no `.env` e falhar sem ela. | A chave não existe no `.env`. Default de dev destrava o ticket; o deploy (16) define o valor real. |
| 04 | Conta demo `demo@toneli.dev.br` criada no lifespan do FastAPI, idempotente. | Migração de dados no Alembic. | Reusa o hash de senha do FastAPI-Users sem duplicar lógica na migração. |
| 04 | `login_failed` via override de `UserManager.authenticate`. Payload só com o e-mail. | Middleware olhando status 400 da rota de login. | FastAPI-Users não tem hook de falha. O override fica no mesmo lugar dos outros eventos. |
| 04 | JWT com validade de 24 h, só Bearer. | Cookie + refresh token. | Aceite pede token em rota protegida. Refresh é YAGNI agora. |
