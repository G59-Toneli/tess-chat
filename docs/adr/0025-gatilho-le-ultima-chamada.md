# ADR 0025 — Gatilho da Compactação lê a última chamada do turno

**Status:** aceito, 2026-09-23. Refina o gatilho do [ADR 0006](0006-compactacao-por-resumo-com-limiar-configuravel.md) ("tokens de entrada do último turno").

## Contexto
`_persistir` gravava em `Message.input_tokens` a soma do `RunUsage` de todas as chamadas ao modelo do turno. O gatilho (`_preparar_historico` → `should_compact`) e a rosca (`GET /api/conversations/{id}/contexto`) liam esse número como tamanho da conversa. Um turno com tool faz várias chamadas, e cada uma reenvia a janela inteira. Turno Notion em prod (msg 222): soma 1.251.511, última chamada ~80k. O turno seguinte compactava com a janela real bem abaixo do limiar, e a rosca mostrava a conversa lotada. Decisão do orquestrador, aprovada pelo Toneli em 23/09.

## Decisão
1. `Message.input_tokens`, `output_tokens`, `thinking_tokens` e `cache_read_tokens` guardam o uso do **último `ModelResponse`** do turno. O input dessa chamada é o tamanho real da janela que o próximo turno herda.
2. O gatilho e a rosca continuam lendo `Message.input_tokens`. Nenhum dos dois muda de código.
3. O custo do turno continua somado: Ledger, `llm_call` e o evento do corte usam o `RunUsage`. Cada `llm_request` (ticket 58) segue com o uso da sua chamada.
4. Vale para todos os caminhos que gravam a Mensagem: fim normal, corte do `ComTeto`, `turn_stopped` (ADR 0023) e retry/fallback. Todos passam por `_persistir`. Parado antes do 1º token não tem `ModelResponse`: a Mensagem fica com o `RunUsage`, como antes.

### Alternativas descartadas
- **Manter a soma e subir o limiar.** Simples, mas o limiar perde o significado de janela. Um turno com 17 chamadas de 75k passa de 1M sem a janela passar de 100k.
- **Gatilho ler o último `llm_request` da Auditoria.** Mesmo número, mas o gatilho passaria a depender de uma tabela de auditoria. A Mensagem já está na mão de quem lê.
- **Coluna nova na Mensagem para a janela.** Pede migração, e a soma já está no Ledger e no `llm_call`.

## Consequências
- Turno de 1 chamada: número idêntico ao de antes.
- O rodapé da Mensagem (`n entrada · n saída`) passa a mostrar a última chamada, não o total do turno. O custo total fica na Auditoria e no Ledger.
- Mensagens gravadas antes deste ADR continuam com a soma. Uma conversa antiga pode compactar uma vez antes da hora no próximo turno.
