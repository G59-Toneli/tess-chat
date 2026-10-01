# 60 — Gatilho da Compactação lê a última chamada do turno

**Type:** task (api/ + web/ se precisar)
**Status:** resolved
**Refs:** ticket 58 (`llm_request`, `docs/LACUNAS.md` seção Compactação), ADR 0006 (Compactação). Pedido do Toneli em 23/09. **Compactação é requisito explícito do desafio: regressão zero.** Roda em paralelo com a outra sessão (ticket 59, migração 0023). Este ticket NÃO cria migração.

**Problema:** `_persistir` grava em `Message.input_tokens` a soma do `RunUsage` de todas as chamadas do turno (`chat.py:256`). O gatilho (`_preparar_historico`, `chat.py:306` → `should_compact`) e a rosca do contexto (`conversas.py:187`) leem esse número como tamanho da conversa. Turno Notion (prod, msg 222): soma 1.251.511, última chamada ~80k. O próximo turno compacta antes da hora e a rosca mostra lotado.

**Decisão (orquestrador, aprovada pelo Toneli em 23/09):** `Message.input_tokens` passa a ser o input da **última** chamada do turno (tamanho real da janela). O custo total do turno continua no Ledger e no `llm_call` (soma, sem mudança). O rodapé da Mensagem passa a mostrar o tamanho do contexto; conferir o rótulo em `web/src/lib/tools.ts:53` e ajustar o texto se ele disser que é custo. Cache e thinking da Mensagem seguem a mesma regra (última chamada) para ficarem coerentes; o Ledger segue somando.

**Aceite:**
1. `_persistir` grava na Mensagem o uso do último `ModelResponse` do turno. Ledger, `llm_call` e `llm_request` inalterados. Turno de 1 chamada: número idêntico ao de hoje.
2. Caminhos que também gravam Mensagem com uso (corte do `ComTeto`/`on_cancel`, `turn_stopped` do ticket 55, retry) seguem a mesma regra.
3. **Regressão da Compactação (modelo fake, CI), antes e depois da mudança. Todos os testes existentes de compactação continuam verdes sem alterar asserção.** Testes novos, observáveis:
   - Turno com N chamadas cuja última está abaixo do limiar e a soma acima → o turno seguinte NÃO compacta.
   - Turno com a última chamada acima do limiar → o turno seguinte compacta (Resumo gravado, evento de auditoria, débito do Resumo no Ledger), igual a hoje.
   - Turno de 1 chamada acima do limiar → compacta exatamente como hoje.
   - Limiar configurável por Configuração continua valendo.
   - A rosca (`/api/conversations/{id}/contexto` ou equivalente) devolve o número da última chamada.
   - Ledger do turno multi-chamada continua com a soma.
4. ADRs 0023 e 0024 estão em uso (0024 reservado pelo ticket 59); crie `docs/adr/0025-gatilho-le-ultima-chamada.md` referenciando o 0006. Atualiza `LACUNAS.md` (fecha o item), `DECISOES-AUTONOMAS.md`, `MOTIVACOES.md`.
5. Suíte em lote: compactação, chat, turnos, medição, crédito, auditoria, contexto, conversas. `tsc` limpo se tocar em web/.

**Tetos:** geração real 0, Jev 0, Tavily 0. Validação real fica com o orquestrador.

## Answer
`_persistir` grava na Mensagem o uso do último `ModelResponse` do turno (input, output, thinking, cache). Ledger, `llm_call` e `llm_request` seguem com a soma e por chamada. Todos os caminhos (fim, corte, `turn_stopped`, retry) passam por `_persistir`. ADR 0025.
Regressão: 21/21 de compactação/contexto/configuração verdes antes e depois, sem mudar asserção. 3 testes novos em `test_compactacao.py` (soma acima e última abaixo não compacta, com rosca e Ledger; última acima compacta; 1 chamada igual ao Ledger). Os 2 multi-chamada ficaram vermelhos antes da mudança.
Ressalvas: mensagens antigas seguem com a soma (sem backfill); parado antes do 1º token fica com o `RunUsage`; `web/` sem mudança (rótulo diz "entrada", não custo).
