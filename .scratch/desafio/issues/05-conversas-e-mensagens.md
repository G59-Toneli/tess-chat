# 05 — Conversas e Mensagens persistidas

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 04
**Refs:** `CONTEXT.md` (Conversa, Mensagem, Anexo).

**What to build:** tabelas `conversations`, `messages` (papel, partes em jsonb, tokens, modelo, criado_em), `attachments` (metadados; arquivo em disco). CRUD REST: listar, criar, renomear, apagar conversa; listar mensagens. Usuário só vê o que é dele.

**Aceite:**
- [x] Usuário A não lê conversa de B (403 ou 404).
- [x] Mensagens voltam na ordem de criação.
- [x] Eventos `conversation_created`, `conversation_deleted`.

## Answer
- Tabelas `conversations`, `messages`, `attachments` (migração 0003) e CRUD em `/api/conversations` (listar, criar, obter, renomear, apagar, listar mensagens), tudo atrás de `current_user`.
- Conversa de outro Usuário responde 404, igual a inexistente. Mensagens ordenadas por `(created_at, id)`.
- Apagar é remoção física com CASCADE. Eventos `conversation_created` e `conversation_deleted` com `conversation_id`.
- Não há rota para criar Mensagem: o ticket 06 grava. Ele também estende `messages` com thinking/cache.
