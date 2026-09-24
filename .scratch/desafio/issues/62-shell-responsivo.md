# 62 — Shell responsivo: Sidebar do shadcn, header mobile, script de checagem

**Type:** task (web/)
**Status:** resolved
**Blocked by:** —
**Refs:** `docs/UI-GUIA.md` (seção Regras, item Responsivo), shadcn Sidebar (https://ui.shadcn.com/docs/components/sidebar).

**Objetivo:** em 390 px o usuário abre e fecha a sidebar por um botão, e nenhuma tela do app tem rolagem horizontal causada pelo shell.

**Causa raiz:** `web/src/layout/AppLayout.tsx` usa um `<aside className="w-72 ...">` fixo dentro do `SidebarProvider`. O comportamento mobile do shadcn (Sheet abaixo de `md`, via `use-mobile.ts`) nunca entra.

## Escopo (só estes arquivos)
- `web/src/layout/AppLayout.tsx`: trocar o `<aside>` por `<Sidebar collapsible="offcanvas">` (`SidebarHeader` com logo, `SidebarContent` com a lista de conversas, `SidebarFooter` com `NavTelas`), e o conteúdo por `<SidebarInset>`. Header ganha `SidebarTrigger` à esquerda, visível só abaixo de `md` (no desktop a sidebar fica sempre aberta, como hoje). No mobile o e-mail do menu do usuário some e fica só o avatar. Navegar (clicar numa conversa, numa tela, em "Nova conversa") fecha o Sheet no mobile (`setOpenMobile(false)`).
- Altura: `h-svh`/`dvh`, nunca `100vh`.
- `web/src/components/ui/*` e `web/src/index.css`: únicos arquivos compartilhados que este ticket pode mexer, e só se preciso (ex.: `DialogContent` com `max-w-[calc(100%-2rem)]` e rolagem interna; `Sheet`). Os tickets 63 a 65 não tocam nesses arquivos.
- `web/scripts/checar-responsivo.mjs` (novo): usa `playwright-core` com o executável do Brave (`C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe`). Recebe base URL, credenciais da conta demo e lista de rotas; para cada rota e cada largura (390x844, 768x1024, 1440x900), em dark: loga, abre, espera rede ociosa, mede `document.documentElement.scrollWidth <= innerWidth` e lista elementos visíveis com `getBoundingClientRect().right > innerWidth + 1` que não estão dentro de container com `overflow-x` auto/scroll/hidden. Salva screenshot em pasta passada por argumento. Sai com código != 0 se houver violação e imprime rota, largura e seletor do culpado. Adicionar `playwright-core` como devDependency se não estiver. Este script é o aceite dos tickets 63 a 66.

## Fora de escopo
Conteúdo das páginas (Chat, tabelas, formulários): tickets 63 a 65.

## Aceite
- `npm run build` limpo.
- Script roda contra o build servido localmente (`vite preview` em porta própria, API local 8000 ou própria) em todas as rotas de `web/src/App.tsx`. Violações que vêm do shell: zero. Violações que vêm de páginas: listar no Answer (vira insumo dos tickets 63 a 65), não corrigir.
- Screenshots em `.scratch/desafio/screens/62-*`: `/` em 390 com sidebar fechada, 390 com sidebar aberta, 1440 igual ao antes (sem regressão visual do desktop).
- Registrar em `docs/DECISOES-AUTONOMAS.md`: corte em `md` (768) e por quê (é o breakpoint do `use-mobile.ts` do shadcn; um só corte, sem layout de tablet próprio).
- Gemini: 0. Não alterar a Configuração da conta demo.

## Answer
- `AppLayout.tsx` usa `Sidebar collapsible="offcanvas"` + `SidebarInset`; abaixo de `md` a sidebar é Sheet aberto pelo `SidebarTrigger` do header, e clicar em conversa, tela, logo ou "Nova conversa" fecha o Sheet (conferido no Brave). E-mail do menu some no mobile; ações da conversa ficam visíveis sem hover. Desktop 1440 igual ao antes (sidebar em 18rem).
- `web/scripts/checar-responsivo.mjs` (playwright-core + Brave, 390/768/1440, dark, `--abrir-sidebar`). Não isenta `overflow-x: hidden` nem container só `overflow-y-*`: isentando, o build antigo passava com a página espremida (DECISOES-AUTONOMAS). No Git Bash: `MSYS_NO_PATHCONV=1` para `--rotas`.
- Rodado em todas as rotas de `App.tsx` (vite preview 4182, API própria 8008, Postgres 5433): shell 0 violações. Antes da mudança: 10 (Config, Auditoria, Créditos, Tools, MCP, Conectores, Compartilhados, Admin), todas pela página espremida.
- Violação de página que sobrou: `/tools` em 390, `span[data-slot=badge]` no `CardTitle` ao lado de nome de tool longo (`stripe_cf8f_get_stripe_account_info`), right=421 e 438. Insumo do 65.
- Primitivos: `DialogContent` com `max-h` em `dvh` e rolagem interna, `PopoverContent` com `max-w` de viewport, Sheet da Sidebar sem foco automático. Screenshots em `.scratch/desafio/screens/62-raiz-*`. Gemini 0. Sem REVISAR(human).
