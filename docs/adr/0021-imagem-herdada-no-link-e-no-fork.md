# ADR 0021 — Imagem herdada no link público e no fork

**Status:** aceito, 2026-09-23. Complementa o ADR 0008 e muda o ADR 0020 no item "anexo vira texto sem bytes".

## Contexto
O link público não mostrava as imagens: o front baixa `/api/attachments/{id}` com Bearer, e o visitante não tem. O fork (ADR 0020) trocava o anexo por `[anexo: nome]`, e o modelo da cópia não via a imagem. É o mesmo cenário do bug do ADR 0016: o modelo descreve o que não vê. Decisão do Toneli em 23/09: a imagem é herdada no link e no fork.

## Decisão
1. **Rota pública do anexo.** `GET /api/s/{share_id}/attachments/{aid}`, sem auth, `X-Robots-Tag: noindex`. Serve só se o share está ativo e o anexo está ligado (`attachments.message_id`) a uma Mensagem da Conversa do share com id até o corte. O join por Mensagem é a checagem de posse: `attachments` não tem `conversation_id`.
2. **404 único.** Share revogado ou inexistente, anexo de outra Conversa, anexo depois do corte, anexo solto (sem Mensagem), id inexistente e arquivo sumido do disco dão o mesmo corpo e o mesmo header (ADR 0008).
3. **O link reescreve a URL.** `GET /api/s/{id}` devolve as parts de arquivo apontando para a rota pública. O front não monta URL e não manda Bearer.
4. **Fork copia o arquivo.** Cada anexo ligado a uma Mensagem copiada vira um Attachment novo do visitante: cópia em disco, id novo, `message_id` da Mensagem copiada. A part aponta para `/api/attachments/{novo_id}`. A cópia é anexo próprio do visitante, então volta com bytes no histórico (ADR 0016). Part sem registro ou sem arquivo continua `[anexo: nome]`.
5. **Revogar não apaga a cópia.** Revogar corta a rota pública na hora. A cópia do fork é do visitante e fica.
6. **Auditoria.** `share_forked` ganha `anexos_copiados` com os ids novos.

### Alternativas descartadas
- **Fork sem bytes (ADR 0020).** A cópia reproduzia o bug do ADR 0016: o modelo inventava o conteúdo da imagem. O argumento "duplica arquivo do dono sem ação do dono" cai porque o dono já publicou a imagem ao compartilhar.
- **Fork apontando para o arquivo do dono (sem cópia).** Revogar ou apagar a Conversa do dono quebraria a Conversa do visitante, e o ADR 0016 só reenvia anexo do próprio Usuário.
- **Token assinado na URL da imagem.** Mais uma chave e expiração para gerir. O id do share já é o segredo de 128 bits.

## Consequências
- Cada fork com imagem duplica os bytes em disco. Limite por arquivo continua 20 MB (upload). Não existe cota de disco por Usuário.
- Quem tem o link baixa a imagem original em tamanho cheio, como já via a Mensagem.
- Download pela rota pública não gera Evento de auditoria: é leitura anônima, igual ao `GET /api/s/{id}`.
