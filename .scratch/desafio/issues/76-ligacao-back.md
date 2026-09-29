# 76 — Ligação no backend: ticket, proxy WebSocket, crédito, auditoria

**Type:** task (api/)
**Status:** blocked
**Blocked by:** 75
**Refs:** ADR 0026, 0027, 0023 (vaga de turno), 0004/0019 (reserva e acerto), 0007 (auditoria). `docs/PROTOCOLO-LIGACAO.md` (contrato, obrigatório). `spike/live/RESULTADO.md` (nomes reais do SDK, obrigatório).

**Objetivo:** o servidor é dono da Ligação. O browser só fala o protocolo.

## Escopo
Código novo em `api/app/voz.py` (router incluído no `main.py`). **Não editar `api/app/chat.py`**: se precisar de algo de lá, importar. Pode editar `turnos.py`, `credito.py`, `config.py` com mudança mínima.
1. `POST /api/voz/ticket` e `WS /api/voz/ws` conforme o protocolo. Ticket em memória, uso único, 30 s.
2. `conectar_gemini()` injetável (padrão `dependency_overrides` ou função substituível). O resto do módulo não conhece o objeto concreto do SDK.
3. Relay nos dois sentidos com duas tasks asyncio (browser→Gemini, Gemini→browser). O fim de uma encerra a outra.
4. A Ligação ocupa a vaga de turno da Conversa (`turnos.reservar`). Uma por Usuário, teto global 3.
5. Limite de 540 s (config). No limite: `fim` com motivo `limite`.
6. Crédito: reserva de 9 min no início; acerto pelo `usageMetadata` no fim; preço de tabela mesmo na chave free. Tabela de Preço ganha o `gemini-3.8-live` com modalidades (próxima migração livre: **0024**).
7. Auditoria: `voice_call_started`, `voice_call_ended` (duração, motivo, tokens por modalidade, custo), `screen_share_started`, `screen_share_stopped`. Não por frame.
8. Config nova `GEMINI_LIVE_API_KEY` (em `config.py` e `.env.example`), mais modelo, voz, limite, fps e resolução como config.
9. Prompt: system prompt do chat + adendo de voz do ADR 0026.
10. Fim único (protocolo seção 5), com `finally`.

A transcrição no histórico e o histórico na Ligação são o ticket 77. Aqui, só guardar as falas em memória na sessão.

## Aceite (pytest com Gemini falso, sem chamada real)
- Ticket inválido, expirado ou reusado → 4401.
- Sem espaço no Cap → 402 no ticket; nada no Ledger.
- Segunda Ligação do mesmo Usuário → 409. Texto `POST /api/chat/{cid}` durante a Ligação → 409.
- Áudio e frame do browser chegam ao Gemini falso; áudio e transcrição do falso chegam ao browser; `interrupted` vira `interrompido`.
- Limite (com limite curto no teste) → `fim` `limite`, vaga liberada.
- Desligar e queda do browser → Ledger com o acerto do uso falso, `voice_call_ended` com o motivo certo, vaga liberada.
- `REVISAR(human)` em: o relay, a validação do ticket, o fim único, o acerto de crédito.
- Chamadas reais: no máximo 2 sessões curtas para smoke local. LEDGER.

## Paradas de estudo
Adicione aqui 4 a 6 entradas no formato do `docs/ESTUDO-VOZ.md`. Obrigatórias: por que proxy e não token efêmero; como o ticket funciona e por que não JWT na URL; por que a Ligação ocupa a vaga de turno; como o relay de duas tasks encerra junto.
