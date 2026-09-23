# ADR 0008 — Compartilhamento por link com corte na última Mensagem

**Status:** aceito, 2026-09-23

## Decisão
Tabela `shares`: id aleatório de 128 bits ou mais, `conversation_id`, `owner_id`, `last_message_id`, `created_at`, `revoked_at`. Rota pública `/s/{id}` sem auth mostra Mensagens até o corte. Revogado ou inexistente devolve o mesmo 404. Header `X-Robots-Tag: noindex`. Mesmo comportamento documentado de ChatGPT e Claude. Sem cópia JSON: o corte basta porque Conversa não é editável.
