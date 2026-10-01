# 65 — Telas de formulário e públicas responsivas

**Type:** task (web/)
**Status:** resolved
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

## Answer
- Grids de cards e campos passam a 1 coluna abaixo de `md` (antes `sm`) em Configuração, Tools por API e MCP. Botões de ação do formulário (Salvar/Descartar, Testar/Salvar, Conectar) ocupam a largura toda no mobile; o campo de URL do MCP empilha com o botão.
- `/tools`: o header do card empilha no mobile, o nome da tool quebra (`break-all`) e o badge desce de linha. Schema ganhou `max-h-96` com rolagem no próprio bloco. `/s/:id`: o botão "Continuar esta conversa" desce abaixo do título no mobile.
- `checar-responsivo.mjs` nas 8 rotas do aceite x 390/768/1440: zero violações (antes 1, o badge de `/tools`). `tsc -b` e `vite build` limpos. Screenshots em `.scratch/desafio/screens/65-*`.
- Ressalvas: o Login atual não tem botão de conta demo (saiu com o cadastro aberto); o card inteiro cabe em 390x844. Linhas rótulo + switch que cabem numa linha (Tema, Ligado do MCP) ficaram inline (DECISOES-AUTONOMAS). Conectores, Login e Placeholder já passavam e não mudaram.
