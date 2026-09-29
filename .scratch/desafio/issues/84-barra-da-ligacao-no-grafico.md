# 84 — Barra da Ligação visível no gráfico de custo

**Type:** bug (web/)
**Status:** resolved
**Blocked by:** —
**Refs:** Answer do 82, `docs/UI-GUIA.md`, `web/src/components/CustoConversa.tsx`, screenshot `.scratch/desafio/screens/82-custo-ligacao-1440.png`.

**Problema:** a barra da origem `ligacao` usa `chart-4`, que quase some no fundo do tema dark.

## Escopo
Trocar a cor da Ligação por uma que contraste nos dois temas e se distinga das outras origens do mesmo gráfico. Preferir um token existente; se nenhum servir, ajustar só o token usado pela Ligação. Não mexer nas cores das outras origens.

## Aceite
- `npm run build` limpo.
- Screenshots no Brave, 1440x900, dark e light, em `.scratch/desafio/screens/84-*`, de uma Conversa com Ligação e pelo menos uma outra origem. Olhar: a barra da Ligação se vê e se distingue.
- Chamadas reais: 0.

## Answer
O tema é todo em cinza e `chart-4` (cinza escuro) sumia no dark e se confundia com `chart-3` no light. Nenhum token cinza serviria, então só `--chart-4` ganhou matiz azul: `oklch(0.55 0.2 255)` no light e `oklch(0.72 0.15 250)` no dark. Só a Ligação usa `chart-4`; as outras origens não mudaram. Build limpo. Screenshots no Brave, 1440x900, com Ligação, Respostas e Resumo do histórico: `.scratch/desafio/screens/84-custo-ligacao-dark-1440.png` e `84-custo-ligacao-light-1440.png`. Ressalva: azul é a única cor fora da escala de cinza do gráfico, de propósito.
