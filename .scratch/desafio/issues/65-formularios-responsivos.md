# 65 — Telas de formulário e públicas responsivas

**Type:** task (web/)
**Status:** blocked
**Blocked by:** 62
**Refs:** `docs/UI-GUIA.md`, ticket 62 (script `web/scripts/checar-responsivo.mjs`).

**Objetivo:** em 390 px o usuário faz login, configura, gerencia tools/MCP/API tools/conectores e abre uma conversa compartilhada sem nada sair da tela.

## Escopo (só estes arquivos)
`web/src/pages/Login.tsx`, `Configuracao.tsx`, `Tools.tsx`, `ApiTools.tsx`, `Mcp.tsx`, `Conectores.tsx`, `Compartilhamento.tsx`, `Placeholder.tsx`.
Não toca `components/ui/*`, `index.css`, `AppLayout.tsx` nem componentes do Chat (ticket 63). Se `/s/:id` usa componentes do ticket 63, só ajusta o container da página.

## O que fazer
- Grids de cards e de campos: 1 coluna abaixo de `md`.
- Linhas "rótulo + controle" (switch, select, slider): empilham no mobile.
- Botões de ação do formulário: largura cheia no mobile.
- Schema/JSON (tools, MCP, resposta do teste de API tool): rolagem dentro do bloco.
- URLs e nomes longos (servidor MCP, host de API tool, escopos Google): truncam ou quebram.
- Login: card centralizado com margem de 16 px; conta demo visível sem rolar em 390x844.

## Aceite
- `npm run build` limpo.
- `checar-responsivo.mjs` em `/login`, `/config`, `/tools`, `/api-tools`, `/mcp`, `/conectores`, `/perfil` e `/s/<shareId existente>`: zero violações em 390, 768 e 1440.
- Screenshots `.scratch/desafio/screens/65-*` em 390 de cada tela.
- Gemini: 0. Não cadastrar nem remover MCP/API tool/conector da conta demo; não alterar a Configuração da conta demo.
