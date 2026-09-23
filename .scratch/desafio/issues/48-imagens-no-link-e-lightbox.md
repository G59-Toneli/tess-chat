# 48 — Imagens no link público e no fork, e imagem clicável que expande

**Type:** task (api/ e web/)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ADR 0008, ADR 0016 (imagem do histórico volta com bytes), ADR 0020 (fork), tickets 09/09b (anexos), 45, 46. `docs/UI-GUIA.md`. Pedido do Toneli em 23/09.

**Problema:**
1. O link público (`/s/<id>`) não mostra as imagens anexadas: `AnexoNaMensagem` baixa de `/api/attachments/{id}` com Bearer, e o visitante não tem. O fork (ticket 46) troca o anexo por `[anexo: nome]`, e o modelo da cópia não vê a imagem.
2. Imagem na mensagem (chat logado e link) não abre em tamanho grande ao clicar.

**Decisão (Toneli, 23/09):** a imagem é herdada no link e no fork. Isso muda o ADR 0020 no ponto "bytes do anexo não são copiados": escrever ADR novo (próximo número livre em `docs/adr/`, confira na hora) que o complementa.

**What to build:**
- Endpoint público `GET /api/s/{share_id}/attachments/{aid}`: sem auth, só se o share está ativo, o anexo pertence à Conversa do share e está ligado a uma Mensagem até o corte (`last_message_id`). Qualquer outro caso: 404 igual. Header `X-Robots-Tag: noindex`. Revogar o link corta o acesso à imagem.
- Página pública desenha as imagens (e PDF como link/ícone, como no chat) usando esse endpoint, sem Bearer.
- Fork: cada anexo das Mensagens copiadas vira um Attachment novo do visitante (cópia do arquivo no disco, novo id), e a parte da Mensagem copiada aponta para `/api/attachments/{novo_id}`. A cópia se comporta como anexo normal do visitante (ADR 0016: volta com bytes no histórico). Revogar o link depois não apaga a cópia. Conferir limite de disco/tamanho já existente.
- Lightbox: clicar na imagem (chat logado, link público, conversa copiada) abre a imagem grande num overlay (componente `Dialog` do shadcn), fecha com Esc, clique fora e botão. Respeitar `prefers-reduced-motion`. Mesmo componente nos três lugares.

**Aceite:**
- [ ] Teste: endpoint público devolve a imagem de share ativo; 404 para revogado, anexo de outra Conversa, anexo depois do corte, id inexistente.
- [ ] Teste: fork copia o anexo como Attachment do visitante, e o 1º turno na cópia recebe a imagem como `BinaryContent` (FunctionModel).
- [ ] Teste: visitante não baixa pelo endpoint autenticado o anexo do dono (continua 404).
- [ ] Screenshots dark no Brave: `48-link-imagem.png` (imagem no link) e `48-lightbox.png` (overlay aberto).
- [ ] ADR escrito. `tsc`/`npm run build` limpos. Sem chamada real a Gemini, Tavily ou Jev.
