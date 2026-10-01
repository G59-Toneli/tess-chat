# 26 — UI: modal de link externo em largura total; sidebar rola junto em /creditos

**Type:** task (AFK, só web/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** `docs/UI-GUIA.md`. Feedback do Toneli em 23/09 de manhã, testando no Brave.

**Problemas:**
1. O modal de confirmação de link externo (abre ao clicar em URL na resposta) ocupa a largura toda da tela. Deve ser um Dialog do shadcn com largura máxima (`sm:max-w-md`), centrado, com URL truncada e botões "Abrir" / "Cancelar".
2. Em `/creditos` (e conferir `/auditoria`, `/admin`, `/config`, `/tools`, `/mcp`, `/conectores`), a página inteira rola e a sidebar de conversas vai junto. O layout deve ter altura fixa da viewport (`h-svh overflow-hidden`), sidebar com scroll próprio e só a área de conteúdo rolando (`overflow-y-auto`). O chat já faz isso; reaproveite o mesmo layout para as páginas internas.

**Aceite:**
- [x] Modal de link externo com largura máxima e centrado. Screenshot dark `26-modal-link.png`.
- [x] Em `/creditos` com conteúdo maior que a viewport, a sidebar fica parada ao rolar. Screenshot `26-creditos-scroll.png` com a página rolada até o fim e a sidebar visível no topo.
- [x] `tsc --noEmit` limpo.

## Answer
- Modal de link: `ModalLink.tsx` (Dialog shadcn, `sm:max-w-md`, URL truncada, Abrir/Cancelar) ligado via `linkSafety.renderModal` do Streamdown no `MessageResponse`. O modal padrão do Streamdown usa classes que o Tailwind não escaneia em node_modules, por isso ficava em largura total.
- Layout: container `h-svh overflow-hidden` e `main` com `overflow-y-auto`. Só a área de conteúdo rola; sidebar fixa em todas as páginas internas (conferido em /creditos, /auditoria, /admin, /config, /tools, /mcp, /conectores e chat: documento sem overflow, sidebar no topo).
- Ressalva: `onConfirm` do Streamdown não fecha o modal; o botão Abrir chama `onClose` depois. `tsc --noEmit -p tsconfig.app.json` limpo. Sem build (web/dist em uso na 8000).
