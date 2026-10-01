# 63 — Chat responsivo: mensagens, barra do input, popovers

**Type:** task (web/)
**Status:** resolved
**Blocked by:** 62
**Refs:** `docs/UI-GUIA.md`, ticket 62 (script `web/scripts/checar-responsivo.mjs`).

**Objetivo:** em 390 px o usuário lê uma conversa longa, com código, tool call e fontes, e usa toda a barra do input sem nada sair da tela.

## Escopo (só estes arquivos)
`web/src/pages/Chat.tsx`, `web/src/components/ai-elements/*`, `SeletorTools.tsx`, `SeletorModelo.tsx`, `IndicadorContexto.tsx`, `CustoConversa.tsx`, `Anexos.tsx`, `BlocoTool.tsx`, `Trabalhando.tsx`, `MarcadorCompactacao.tsx`, `RascunhoEmail.tsx`, `ModalLink.tsx`, `ItemCompartilhar.tsx`, `estados.tsx`.
Não toca `components/ui/*`, `index.css` nem `AppLayout.tsx`.

## O que checar
- Barra do input: botões (anexo, tools, modelo, contexto, custo, enviar) cabem ou quebram em duas linhas; nenhum some sem alternativa. Se não couber, agrupar os secundários num menu "mais".
- Popovers (tools, modelo, contexto, custo) cabem em 390 (largura limitada a `calc(100vw-2rem)`, `collisionPadding`).
- Bloco de código e JSON de tool: rolagem horizontal dentro do bloco, não na página.
- Mensagem longa sem espaço (URL, hash): `break-words` / `overflow-wrap:anywhere`.
- Cabeçalho da conversa (título, compartilhar) trunca.
- Estado vazio da conversa (sugestões) em coluna única.

## Aceite
- `npm run build` limpo.
- `checar-responsivo.mjs` em `/` e `/c/<id de conversa demo existente com código e tool call>`: zero violações em 390, 768 e 1440.
- Screenshots `.scratch/desafio/screens/63-*` em 390: conversa com código e tool, popover de tools aberto, popover de modelo aberto.
- **Gemini: 0.** Usar conversa que já existe na conta demo. Não enviar turno. Não alterar a Configuração da conta demo.

## Answer
- `checar-responsivo.mjs` em `/`, `/c/a365ff43…` (10 tools Stripe) e `/c/ed38ac56…` (web_search, fontes): 0 violações em 390/768/1440, antes e depois. O script não via os defeitos: o scroller da `Conversation` tem `overflow-x: auto` e isenta o chat inteiro. Prova por sonda descartável (Brave): tools expandidas, bloco de código, 4 popovers/dialog abertos, texto cortado por `overflow-hidden`.
- Corrigido: URL e hash longos sumiam no `overflow-hidden` do `MessageContent` (o `wrap-anywhere` do Streamdown não compila); agora `wrap-anywhere` no `MessageContent`. Nome da tool virava "str…" em 390: rótulo do status só ícone abaixo de `md`. Barra do input e itens do menu de modelo com 40 px de altura abaixo de `md`.
- Barra cabe numa linha em 390 (largura dos ícones fica 32 px); sem menu "mais". Popovers já cabiam (primitivo do 62). Estado vazio já era coluna única. Cabeçalho da conversa em 390 não tem título: mora no `AppLayout.tsx`, fora do escopo.
- Ressalva: nenhuma conversa demo tem bloco de código; o print `63-conversa-codigo-tool-390.png` tem um bloco injetado só no browser (`page.route`). Custo com dado também é resposta simulada: a API na 8000 é anterior ao endpoint de custo (404). Gemini 0.
