# ADR 0018 — Fallback só entre modelos Gemini, sem OpenAI

**Status:** aceito, 2026-09-23. Revisa o item 2 do ADR 0012.

## Contexto
O ADR 0012 pôs OpenAI no fim da cadeia de fallback, "se `OPENAI_API_KEY` existir". A chave não existe. Nada no código lê essa variável (`api/app/chat.py`). O README e a LACUNAS listavam isso como lacuna.

## Decisão
Toneli, 23/09: sem fallback OpenAI.
1. **Cadeia:** `gemini-3.8-flash` → `gemini-3.7-flash`. Nada além.
2. **Retry com backoff e jitter** continua como no ADR 0012 (tenacity, `api/app/resiliencia.py`).
3. O resto do ADR 0012 (erros transitórios, auditoria `llm_call`, `llm_retry`, `llm_fallback`) fica igual.

### Alternativas descartadas
- **OpenAI no fim da cadeia.** Sem chave, é código morto. Ativar pede chave paga, linha na Tabela de Preço e teste do stream de outro provedor. Custo real para um cenário que a demo não exercita.
- **Deixar o ADR 0012 prometendo OpenAI.** Documento que diverge do código vira pergunta sem resposta na entrevista.

## Consequências
- Queda do Google inteiro derruba o chat. Os dois modelos dependem do mesmo provedor e da mesma chave.
- A Tabela de Preço fica só com preços Gemini.
- Voltar a ter terceiro provedor pede um ADR novo.
