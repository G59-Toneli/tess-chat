# ADR 0027 — Crédito da Ligação: reserva de 9 min, acerto pelo uso real, preço de tabela mesmo na chave free

**Status:** aceito, 2026-09-28. Estende os ADRs 0004 e 0019 para a Ligação (ADR 0026).

## Contexto
A Ligação cobra por áudio de entrada, imagem de entrada e áudio de saída, com preços diferentes (pricing de 28/09 do `gemini-3.8-live`: áudio in US$ 3/1M, imagem in US$ 1/1M, áudio out US$ 12/1M, texto US$ 0,75 in e 4,50 out). No free tier o custo real é zero. Se o Cap contasse zero, ele nunca dispararia.

## Decisão
Toneli, 28/09:
1. **Preço de tabela sempre.** O débito usa o preço pago, qualquer que seja a chave. O Crédito mede "quanto custaria", e o Cap continua demonstrável.
2. **Reserva no início:** o custo máximo de 9 min de Ligação (~US$ 0,25). Sem espaço no Cap, o ticket da Ligação é recusado com 402.
3. **Acerto no fim** pelo `usageMetadata` que o Gemini reporta, por modalidade. Uma linha no Ledger.
4. A Tabela de Preço ganha o `gemini-3.8-live`, com as modalidades separadas.

### Alternativas descartadas
- **Cobrar o custo real da chave (zero no free).** O Cap vira decoração.
- **Derrubar a Ligação no meio quando o saldo acaba.** Mais código para um caso que a demo não mostra. A reserva de 9 min já garante que a Ligação cabe no Cap.

## Consequências
- A reserva segura ~US$ 0,25 durante a Ligação, mesmo que ela dure 30 s.
- Se o Gemini não reportar uso (queda), o acerto usa a estimativa por duração. O agente registra o critério em DECISOES-AUTONOMAS.
