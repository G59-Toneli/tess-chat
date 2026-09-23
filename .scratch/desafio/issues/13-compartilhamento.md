# 13 — Compartilhar conversa por link público

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 07
**Refs:** ADR 0008.

**What to build:** tabela `shares`, `POST /api/conversations/{id}/share`, `DELETE` para revogar, `GET /s/{share_id}` público servindo a view read-only com mensagens até o corte. Header noindex. Eventos `share_created`, `share_revoked`. Front: botão compartilhar, lista "meus links".

**Aceite:**
- [x] Link abre em janela anônima sem login.
- [x] Mensagem enviada depois do share não aparece no link.
- [x] Revogado e inexistente devolvem 404 idênticos.

## Answer
Tabela `shares` (migração 0007), `app/shares.py`: `POST /api/conversations/{id}/share`, `GET /api/shares`, `DELETE /api/shares/{id}`, `GET /api/s/{id}` público (JSON) e `GET /s/{id}` servindo o front, ambos com `X-Robots-Tag: noindex`. Eventos `share_created` e `share_revoked`.
Front: item Compartilhar no menu da Conversa (toast com cópia), `/s/:shareId` read-only com banner "compartilhada por", `/compartilhados` com abrir, copiar, revogar e estados vazio/carregando/erro.
Ressalva: "compartilhada por" mostra só a parte do e-mail antes do `@`. Cada clique cria link novo.
REVISAR(human): 404 único em `_share_ativo` e o corte por `max(messages.id)` em `criar`.
Screenshots: `.scratch/desafio/screens/13-*.png`.
