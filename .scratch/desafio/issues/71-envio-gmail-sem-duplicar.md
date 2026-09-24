# 71 — Envio do Gmail não duplica em timeout

**Type:** bug (api/, web/)
**Status:** open
**Refs:** `api/app/conectores.py` (`enviar_rascunho`), ADR 0013, revisão de 24/09.

**Problema:** o Gmail pode enviar e a resposta se perder (timeout). O Rascunho fica `pendente`, o usuário clica de novo e o destinatário recebe dois e-mails. A trava de linha só cobre clique simultâneo.

## Escopo
1. Estado `enviando` gravado antes do POST ao Gmail. Timeout deixa `enviando` e o card pede para conferir no Gmail em vez de reenviar.

## Aceite
- Teste: timeout no envio não deixa o Rascunho reenviável.
