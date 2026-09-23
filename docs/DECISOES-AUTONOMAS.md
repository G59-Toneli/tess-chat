# Decisões autônomas

Decisões fora dos ADRs, tomadas pelo agente executor. Formato: ticket, decisão, alternativa descartada, por quê.

| ticket | decisão | alternativa descartada | por quê |
|---|---|---|---|
| 04 | `JWT_SECRET` e `DEMO_PASSWORD` com default de dev em `app/config.py`. Produção sobrescreve no `.env`. | Exigir a chave no `.env` e falhar sem ela. | A chave não existe no `.env`. Default de dev destrava o ticket; o deploy (16) define o valor real. |
| 04 | Conta demo `demo@toneli.dev.br` criada no lifespan do FastAPI, idempotente. | Migração de dados no Alembic. | Reusa o hash de senha do FastAPI-Users sem duplicar lógica na migração. |
| 04 | `login_failed` via override de `UserManager.authenticate`. Payload só com o e-mail. | Middleware olhando status 400 da rota de login. | FastAPI-Users não tem hook de falha. O override fica no mesmo lugar dos outros eventos. |
| 04 | JWT com validade de 24 h, só Bearer. | Cookie + refresh token. | Aceite pede token em rota protegida. Refresh é YAGNI agora. |
| 05 | Conversa de outro Usuário responde 404. Filtro por `user_id` na própria query. | 403. | 404 não revela que a Conversa existe. Um caminho de código só. |
| 05 | Apagar Conversa é remoção física, CASCADE para Mensagens e Anexos. | Soft delete com `deleted_at`. | Aceite não pede recuperação. O Evento de auditoria guarda o `conversation_id`. |
| 05 | Mensagens ordenadas por `(created_at, id)`, `id` bigserial. | Só `created_at`. | `now()` é fixo na transação; o 06 grava usuário e assistente juntos. |
| 05 | `attachments` com `user_id` e `message_id` nulo. | `message_id` obrigatório. | O 09 faz upload antes da Mensagem existir. |
| 05 | Rotas em `/api/conversations`. | Sem prefixo `/api`. | Casa com `/api/chat` do 06 e separa da SPA do 07a. |
