# ADR 0004 — Crédito em micro-dólar inteiro, debitado do uso real, com Ledger somente-inserção

**Status:** aceito, 2026-09-23. Reserva revisada pelo [ADR 0019](0019-reserva-por-estimativa-local.md).

## Contexto
Requisito: cap de créditos com contabilização. Toneli exige número confiável: "sei que gastei X centavos".

## Opções
1. Tokens brutos. Não compara Gemini com Jev.
2. Dinheiro, calculado de estimativa local.
3. Dinheiro, calculado do `usage_metadata` real do provedor vezes a Tabela de Preço vigente.

## Decisão
Opção 3, em micro-dólar inteiro (1 USD = 1.000.000). Sem float. Uma linha no Ledger por chamada: tokens de entrada, saída, thinking, cache, modelo, preço aplicado, custo. Saldo é a soma do Ledger. Cap por Usuário e global.

Fluxo: **reserva** antes da chamada (estimativa de entrada mais `max_output_tokens`), **acerto** depois com o valor real. Reserva que estoura o cap recusa a chamada antes de gastar.

## Consequências
- Depende de saber se `usage_metadata` vem no último chunk do stream e se thinking está dentro de `candidatesTokenCount`. Ticket 01 testa.
- Teste de aceitação: soma do Ledger bate com a soma dos `usage_metadata` gravados.

## Revisão (2026-09-23)
O código não grava uma linha por chamada ao modelo. Grava uma linha por turno e linhas à parte para os outros consumos:
- **Turno do Gemini:** uma linha, com o `RunUsage` somado de todos os requests do turno (tool calls incluídas), o `message_id` da resposta e o preço do último modelo que respondeu (`_persistir` em `api/app/chat.py`).
- **Roteador:** uma linha `jev-latest`, sem `message_id` (`_rotear` em `chat.py`).
- **Resumo da Compactação:** uma linha `gemini-3.1-flash-lite`, sem `message_id` (`api/app/compactacao.py`).

Os três passam por `acertar()` em `api/app/credito.py`.

**Por quê:** decisão do ticket 06b (`docs/DECISOES-AUTONOMAS.md`). Os dois Gemini da cadeia têm o mesmo preço, então somar o turno ao preço do último modelo não muda o valor. OpenAI saiu da cadeia ([ADR 0018](0018-fallback-so-entre-geminis.md)). O detalhe por request fica na auditoria: `llm_call`, `llm_retry` e `llm_fallback` ([ADR 0007](0007-auditoria-append-only.md), [ADR 0012](0012-resiliencia-retry-e-fallback-de-modelo.md)). Dinheiro no Ledger, história na auditoria.

**Custo:** se a cadeia ganhar modelo com preço diferente, o turno misto passa a ser cobrado errado. Aí o Ledger precisa de uma linha por request.
