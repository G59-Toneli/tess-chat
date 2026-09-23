# 09 — Anexos: imagem e PDF no chat

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 07
**Refs:** `research/02` §1.5.

**What to build:** upload em `POST /api/attachments` (limite 20 MB, tipos png/jpg/webp/pdf), arquivo em `data/attachments/`, metadados em `attachments`. Mensagem referencia anexos. Ao chamar o modelo, anexos viram `BinaryContent` com `media_resolution` medium para PDF. Front: botão de anexo no prompt-input, preview.

**Aceite:**
- [ ] Enviar imagem e perguntar "o que tem aqui" devolve descrição coerente.
- [ ] Enviar PDF de 3 páginas e pedir resumo devolve conteúdo do PDF.
- [ ] Tipo não permitido é recusado com 415.
