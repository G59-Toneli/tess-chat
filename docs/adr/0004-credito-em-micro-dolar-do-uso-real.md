# ADR 0004 — Crédito em micro-dólar inteiro, debitado do uso real, com Ledger somente-inserção

**Status:** aceito, 2026-09-23

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
