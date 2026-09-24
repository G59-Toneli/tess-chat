# 64 — Telas de tabela responsivas

**Type:** task (web/)
**Status:** blocked
**Blocked by:** 62
**Refs:** `docs/UI-GUIA.md`, ticket 62 (script `web/scripts/checar-responsivo.mjs`).

**Objetivo:** em 390 px o usuário lê auditoria, créditos, admin e compartilhados sem a página rolar para o lado.

## Escopo (só estes arquivos)
`web/src/pages/Auditoria.tsx`, `Creditos.tsx`, `Admin.tsx`, `Compartilhados.tsx`.
Não toca `components/ui/*`, `index.css` nem `AppLayout.tsx`.

## O que fazer
- Tabela: abaixo de `md`, lista de cards (campos principais) ou tabela dentro de container `overflow-x-auto` com colunas secundárias escondidas (`hidden md:table-cell`). Cards quando a linha tem ação; rolagem quando é consulta densa (auditoria). Registrar a escolha em DECISOES-AUTONOMAS.
- Filtros da auditoria: empilham em coluna; drawer de payload ocupa a largura toda no mobile (JSON rola dentro dele).
- Gráficos de créditos: largura 100%, legenda legível em 390.
- Cards de saldo/cap: grid de 1 coluna no mobile.
- Cabeçalho da página (título + ações): quebra linha.

## Aceite
- `npm run build` limpo.
- `checar-responsivo.mjs` nas 4 rotas: zero violações em 390, 768 e 1440 (admin só se a conta demo for superuser; senão registrar).
- Screenshots `.scratch/desafio/screens/64-*` em 390 de cada tela, mais o drawer da auditoria aberto.
- Gemini: 0. Não alterar a Configuração da conta demo.
