# 70 — Share criado no meio do turno

**Type:** bug (api/)
**Status:** open
**Refs:** `api/app/shares.py` (`criar`), ADR 0023, revisão de 24/09.

**Problema:** a pergunta é gravada no início do turno. Share criado enquanto o modelo responde usa o maior id da hora: o link mostra a pergunta sem a resposta.

## Escopo
1. Com turno ativo na Conversa (`turnos.ATIVOS`), cortar antes da última pergunta ou responder 409. Escolher, registrar em DECISOES-AUTONOMAS.

## Aceite
- Teste: share durante o turno não expõe pergunta sem resposta.
