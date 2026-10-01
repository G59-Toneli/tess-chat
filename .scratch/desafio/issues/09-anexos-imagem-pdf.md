# 09 — Anexos: imagem e PDF no chat

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 07
**Refs:** `research/02` §1.5.

**What to build:** upload em `POST /api/attachments` (limite 20 MB, tipos png/jpg/webp/pdf), arquivo em `data/attachments/`, metadados em `attachments`. Mensagem referencia anexos. Ao chamar o modelo, anexos viram `BinaryContent` com `media_resolution` medium para PDF. Front: botão de anexo no prompt-input, preview.

**Aceite:**
- [x] Enviar imagem e perguntar "o que tem aqui" devolve descrição coerente.
- [x] Enviar PDF de 3 páginas e pedir resumo devolve conteúdo do PDF.
- [x] Tipo não permitido é recusado com 415.

## Answer
- `POST /api/attachments` (tipo pelos bytes mágicos, 415/413), `GET /api/attachments/{id}` só do dono; arquivo em `data/attachments/`, evento `attachment_uploaded`. Em `chat.py`, uma chamada a `montar_anexos` troca a referência por data URI; o adapter vira `BinaryContent`, PDF com `media_resolution` medium por parte (formato `{level}`, provado no body HTTP).
- Front: botão de anexo, chips com remover, miniatura da imagem e chip de PDF na Mensagem. Manual no Brave com 2 chamadas Gemini: imagem descrita certo, PDF de 3 páginas resumido página a página.
- Ressalvas: o base64 do anexo fica gravado em `messages.parts` (o `_persistir` salva o prompt como veio) e volta ao modelo e à estimativa de reserva nos turnos seguintes; `attachments.message_id` fica nulo. Nome do PDF some no histórico recarregado ("Documento").
