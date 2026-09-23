# 13 — Compartilhar conversa por link público

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 07
**Refs:** ADR 0008.

**What to build:** tabela `shares`, `POST /api/conversations/{id}/share`, `DELETE` para revogar, `GET /s/{share_id}` público servindo a view read-only com mensagens até o corte. Header noindex. Eventos `share_created`, `share_revoked`. Front: botão compartilhar, lista "meus links".

**Aceite:**
- [ ] Link abre em janela anônima sem login.
- [ ] Mensagem enviada depois do share não aparece no link.
- [ ] Revogado e inexistente devolvem 404 idênticos.
