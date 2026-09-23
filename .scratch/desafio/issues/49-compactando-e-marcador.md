# 49 — "Compactando histórico…" no turno que compacta e marcador sem reload

**Type:** task (api/ e web/)
**Status:** resolved
**Refs:** ticket 12 (Compactação), ADR 0006, ticket 37 (indicador de trabalhando). Pedido do Toneli em 23/09.

**Problema:** durante o Resumo a tela mostrava "Pensando…". O `ProcessHistory` roda antes do request do modelo, e o `chat()` esperava o 1º evento do modelo antes de abrir a resposta, então nada saía na rede durante o Resumo. O separador "Histórico compactado aqui" só aparecia depois de um reload, porque o corte ficava em cache no módulo.

**Decisão:** no turno que compacta, o stream abre antes do modelo. Uma parte `data-compactando` (id fixo `compactacao`) sai logo depois do `start` com `feita: false` e vira `feita: true` antes do 1º chunk do modelo. Ela não vai para o banco. Trade-off: nesse turno, falha do provedor chega como erro no stream (texto genérico em pt-BR), não como 502 JSON. Turno sem compactação não muda. Alternativa descartada: rodar o Resumo fora do agente, antes do stream (contraria o ProcessHistory do ADR 0006).

## Answer
Back: `_com_compactando` em `api/app/chat.py`. O pré-fetch do 1º evento (que gera o 502) só roda quando não há Compactação. Teste novo em `tests/test_compactacao.py`: o aviso sai só no turno que compacta, `false` e depois `true`, antes do `text-start`.
Front: `Chat.tsx` mostra "Compactando histórico…" enquanto `feita` for false. O corte virou estado do `ChatConversa` e é buscado de novo no `onFinish` de um turno que compactou. `idNoChat` traduz o id do banco para o id do useChat pela posição em `juntarTurnos`. Se as listas não batem, não marca.
Validado no browser local (API com o código novo em :8010, Flash-Lite), com 3 chamadas ao chat e 1 ao Resumo: a página mostrou "Pensando…", depois "Compactando histórico…", depois o separador sem reload. Screenshot: `screens/49-marcador-sem-reload.png`.
E2E em produção (chat.toneli.dev.br, deploy de `ee0f4a3`, conta `e2e-49@teste.dev`, Flash-Lite), com 4 chamadas ao chat e 1 ao Resumo: a página mostrou "Pensando…", depois "Compactando histórico…", depois o separador. Todas as mensagens vieram pelo stream, e o separador caiu depois da 1ª resposta (corte `ate_message_id` 122), sem reload. A resposta "Seu nome é Ana e você gosta de xadrez." veio do Resumo. Screenshot: `screens/49-e2e-producao.png`.
