# 26 — UI: modal de link externo em largura total; sidebar rola junto em /creditos

**Type:** task (AFK, só web/)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** `docs/UI-GUIA.md`. Feedback do Toneli em 23/09 de manhã, testando no Brave.

**Problemas:**
1. O modal de confirmação de link externo (abre ao clicar em URL na resposta) ocupa a largura toda da tela. Deve ser um Dialog do shadcn com largura máxima (`sm:max-w-md`), centrado, com URL truncada e botões "Abrir" / "Cancelar".
2. Em `/creditos` (e conferir `/auditoria`, `/admin`, `/config`, `/tools`, `/mcp`, `/conectores`), a página inteira rola e a sidebar de conversas vai junto. O layout deve ter altura fixa da viewport (`h-svh overflow-hidden`), sidebar com scroll próprio e só a área de conteúdo rolando (`overflow-y-auto`). O chat já faz isso; reaproveite o mesmo layout para as páginas internas.

**Aceite:**
- [ ] Modal de link externo com largura máxima e centrado. Screenshot dark `26-modal-link.png`.
- [ ] Em `/creditos` com conteúdo maior que a viewport, a sidebar fica parada ao rolar. Screenshot `26-creditos-scroll.png` com a página rolada até o fim e a sidebar visível no topo.
- [ ] `tsc --noEmit` limpo.
