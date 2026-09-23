# 47 — Seletor de modelo e raciocínio na barra do input

**Type:** task (web/)
**Status:** resolved
**Refs:** ticket 14 (Configuração por Usuário e por Conversa). Pedido do Toneli em 23/09.

**Decisão (Toneli, 23/09):** o modelo e o nível de raciocínio ficam na barra do input, não só em `/config`. O `PromptInput` do AI Elements fica. Da prompt bar de referência entra só o estilo do menu: seções, destaque que desliza, check no item escolhido. Numa conversa nova, a escolha fica em memória e é aplicada no settings da Conversa quando ela é criada. O padrão da conta não muda. Alternativa descartada: trocar o composer inteiro pela barra de referência (o @, o / e o ditado dela são demo, os tokens não existem aqui e o UI-GUIA pede AI Elements). Alternativa descartada: gravar na conta quando não há Conversa (mudaria todas as conversas que herdam da conta).

## Answer
`web/src/components/SeletorModelo.tsx`: botão `3.8 Flash · Médio ⌄` no rodapé do input, com popover Modelo / Raciocínio e o link "Mais opções" para `/config`. Com Conversa, faz PUT em `/api/conversations/{id}/settings`, com update otimista e rollback. Sem Conversa, `ChatNovo` guarda a escolha e faz o PUT logo depois de `criarConversa`, antes do primeiro envio.
Screenshots: `screens/47-seletor-modelo-aberto.png`, `screens/47-seletor-modelo-escolhido.png`.
Validado no browser em 23/09, ambiente local (web :5199, api :8000), com 1 chamada ao Gemini: Flash-Lite + Mínimo escolhidos em `/` gravaram no settings da Conversa nova, e a resposta saiu com `model: gemini-3.1-flash-lite`. Trocar para Alto numa Conversa existente gravou `high` nela. O settings da conta ficou `null` nos dois casos.
