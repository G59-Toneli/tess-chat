# 68 — Reserva conta o peso do PDF

**Type:** bug (api/)
**Status:** open
**Refs:** `api/app/chat.py` (`_estimar_input`), `api/app/anexos.py:112`, revisão dos REVISAR(human) de 24/09.

**Problema:** `_estimar_input` soma `TOKENS_IMAGEM` por imagem, mas o PDF também vai com os bytes ao modelo (ADR 0016) e entra na estimativa quase como zero. A reserva sai menor que o custo real e o Cap pode estourar.

## Escopo
1. Somar um peso por PDF na estimativa (por página ou fixo). Medir o input real de um PDF conhecido antes de escolher o número; registrar em DECISOES-AUTONOMAS.

## Aceite
- Teste: conversa com PDF anexado reserva mais que a mesma conversa sem o PDF.
