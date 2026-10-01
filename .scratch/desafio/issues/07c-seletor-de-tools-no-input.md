# 07c — Seletor de tools junto da área de input

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 09
**Refs:** `docs/UI-GUIA.md`. Feedback do Toneli em 23/09 à noite.

**What to build:** o painel lateral "Tools da conversa" (07b) sai. O controle de tools vai para a barra do prompt-input: um botão com ícone de ferramenta e contador ("2 tools") ao lado do botão de anexo; ao clicar, popover com a lista de tools e switches, mais o link "Gerenciar tools". Mesma API de toggle. Manter o espaço do chat sem coluna à direita. Se o 09 colocou o botão de anexo na barra, alinhe os dois.

**Aceite:**
- [x] Popover abre a partir da barra do input, liga e desliga tools, e o chat ocupa a largura toda.
- [x] Screenshot dark: `07c-popover-tools.png`.

## Answer
- `PainelTools` virou `SeletorTools`: botão "N tools" na barra do input, ao lado do clipe do 09, abre popover (shadcn) com switches e o link "Gerenciar tools". Mesma API de toggle do 07b.
- `LayoutChat` perdeu a coluna `painel`; sem `aside` à direita. O contador conta só tools ligadas na conversa e ligadas no global.
- Verificado no Brave: PUT 200, contador vai de 2 para 1 e volta, sem overflow horizontal. Screenshot `screens/07c-popover-tools.png`.
- Ressalva: o `::after` do Switch (área de toque) estourava a lista rolável e cortava o texto; resolvido com `-mr-4 pr-4` na lista.
