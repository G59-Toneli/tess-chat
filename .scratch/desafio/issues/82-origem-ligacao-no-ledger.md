# 82 — Origem `ligacao` no Ledger e no custo da Conversa

**Type:** task (api/ + web/)
**Status:** resolved
**Blocked by:** 78
**Refs:** ADR 0027. Ressalva 2 do ticket 76.

**Problema:** o débito da Ligação entra no Ledger com origem `compactacao`, porque `CustoConversa.tsx` quebra com origem desconhecida. O custo da Conversa mostra a Ligação como Compactação. Isso aparece no vídeo de demo.

## Escopo
1. Origem `ligacao` no débito de `api/app/voz.py` (e no enum ou check do banco, se houver; migração livre: 0025).
2. `CustoConversa.tsx` (e onde mais a origem é lida) mostra "Ligação". Origem desconhecida não quebra: mostra o nome cru.

## Aceite
- pytest: acerto da Ligação grava origem `ligacao`.
- `npm run build` limpo; screenshot Brave dark 1440x900 do custo de uma Conversa com Ligação em `.scratch/desafio/screens/82-*`.
- Chamadas reais: 0.

## Paradas de estudo
Nenhuma obrigatória.

## Answer
Sem coluna nem migração: a origem já sai da linha do Ledger (`credito.py`). Linha sem `message_id` com o modelo Live vira `ligacao`; o resto segue como antes. Front: `ligacao` em `OrigemGasto`, rótulo "Ligação"; origem desconhecida mostra o nome cru (`origemDe`). Testes: `test_credito` e `test_voz` (fluxo real do desligar) afirmam `ligacao`. Migração 0025 não foi usada. Nenhum `REVISAR(human)` novo. Screenshot: `.scratch/desafio/screens/82-custo-ligacao-1440.png`.
