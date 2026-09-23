# 05 — Conversas e Mensagens persistidas

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 04
**Refs:** `CONTEXT.md` (Conversa, Mensagem, Anexo).

**What to build:** tabelas `conversations`, `messages` (papel, partes em jsonb, tokens, modelo, criado_em), `attachments` (metadados; arquivo em disco). CRUD REST: listar, criar, renomear, apagar conversa; listar mensagens. Usuário só vê o que é dele.

**Aceite:**
- [ ] Usuário A não lê conversa de B (403 ou 404).
- [ ] Mensagens voltam na ordem de criação.
- [ ] Eventos `conversation_created`, `conversation_deleted`.
