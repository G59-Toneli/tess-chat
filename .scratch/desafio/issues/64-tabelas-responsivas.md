# 64 — Telas de tabela responsivas

**Type:** task (web/)
**Status:** resolved
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

## Answer
- Auditoria: tabela fica com rolagem horizontal (consulta densa); abaixo de `md` somem Usuário, Modelo, Tokens e Latência, que estão no drawer. Filtros empilham em coluna com largura total. Drawer ocupa 390 inteiro (`data-[side=right]:w-full`, porque o `w-3/4` do Sheet tem variante e não caía com `w-full`); JSON rola dentro dele.
- Admin: Usuários viram cards abaixo de `md` (linha tem ação: Editar Cap, Ver eventos); tabela só em `md+`. Créditos: Resumo em 1 coluna até `lg` (em 768 com sidebar os 3 números encostavam), cabeçalho quebra linha, Ledger esconde Raciocínio e Cache no mobile. Compartilhados já era lista; só padding e alvo de toque.
- Todas as 4: padding `p-4 md:p-8`; botões de ação/paginação com 40 px no mobile (UI-GUIA).
- `checar-responsivo.mjs` nas 4 rotas x 390/768/1440: 0 violações. Ressalva: já dava 0 antes (o `Table` do shadcn já rola em x); o defeito real era sobreposição do Resumo, que o script não mede. Conferido no olho por screenshot.
- Demo local é superuser no Postgres 5433 (API da 8000 é antiga e não rebaixa), então /admin foi medido com dados. Screenshots `.scratch/desafio/screens/64-*` + `64-auditoria-390-drawer.png`. Gemini 0. Sem REVISAR(human).
