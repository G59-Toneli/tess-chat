# 63 — Chat responsivo: mensagens, barra do input, popovers

**Type:** task (web/)
**Status:** blocked
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
