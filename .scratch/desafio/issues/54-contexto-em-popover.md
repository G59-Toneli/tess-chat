# 54 — Detalhe do contexto em popover no clique

**Type:** task (web/)
**Status:** resolved
**Refs:** ticket 53. Pedido do Toneli em 23/09.

**Problema:** a tooltip da rosca era uma frase longa, com tudo junto e sem hierarquia. Ela também só abria no hover.

**Decisão (Toneli, 23/09):** a rosca abre um popover no clique, com as informações em blocos: percentual, barra, tokens, uma frase do que acontece, modelo e janela à parte, e um link para mudar o limite.

## Answer
`IndicadorContexto.tsx`: Popover do shadcn no lugar da Tooltip. O componente `Detalhe` mostra o título e o percentual na cor da faixa, a barra, "X de Y tokens", "Faltam Z tokens para resumir as mensagens antigas." (ou "Passou do limite…"), uma `dl` com o modelo e a janela, e o link "Mudar o limite" para `/config?conversa=<id>`. Os estados vazio e de erro têm uma frase curta. O `aria-label` é "Contexto: N % até resumir". Em `lib/contexto.ts`, o `resumo` virou `porcento`.
Validado no browser local, sem custo: `screens/54-contexto-popover.png`.
