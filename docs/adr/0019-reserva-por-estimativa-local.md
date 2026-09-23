# ADR 0019 — Reserva de crédito por estimativa local, sem `count_tokens`

**Status:** aceito, 2026-09-23. Revisa o fluxo de reserva do ADR 0004. O acerto pelo uso real fica igual.

## Contexto
O ADR 0004 manda reservar antes da chamada com "estimativa de entrada mais `max_output_tokens`". Não diz como estimar. O código estima localmente: ~3 caracteres por token sobre as partes, mais `TOKENS_IMAGEM` por imagem (`_estimar_input` em `api/app/chat.py`; ADR 0016). O spike H5 provou que `UsageLimits(count_tokens_before_request=True)` funciona. A LACUNAS pedia decidir: emendar o ADR ou trocar para `count_tokens`.

## Decisão
Toneli, 23/09: a reserva segue com a estimativa local, ~3 caracteres por token (INFERIDO: razão não medida contra o tokenizer do Gemini).

Por quê:
1. **A reserva só segura crédito.** A cobrança final usa o `usage` real do provedor (ADR 0004). Erro da estimativa não vira erro de cobrança; no máximo recusa ou aceita um turno perto do Cap.
2. **`count_tokens` custa uma ida de rede por turno**, antes do primeiro token. Latência a mais em todo turno.
3. **`count_tokens` é mais um ponto de falha.** Se ele cair, o fallback seria a própria estimativa local.

### Alternativas descartadas
- **`count_tokens` antes de cada request.** Número exato, mas paga latência e risco para melhorar uma reserva que o acerto já corrige.
- **`UsageLimits(count_tokens_before_request=True)`.** Mesmo custo de rede. Limita tokens, não dinheiro. O `FunctionModel` dos testes não implementa (`docs/DECISOES-AUTONOMAS.md`, 08).

## Consequências
- Perto do Cap, a reserva pode recusar um turno que caberia, ou aceitar um que estoura um pouco. O acerto grava o valor real.
- Duas chamadas simultâneas do mesmo Usuário ainda passam juntas do Cap. Lacuna separada, fora deste ADR.
