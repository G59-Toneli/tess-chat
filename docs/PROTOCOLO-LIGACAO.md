# Protocolo da Ligação (browser ⇄ backend)

Contrato entre `web/` (ticket 78) e `api/app/voz.py` (ticket 76). Os dois lados seguem este arquivo. Mudança aqui exige atualizar os dois tickets. Gemini ⇄ backend fica em `spike/live/RESULTADO.md`.

## 1. Ticket de Ligação
`POST /api/voz/ticket` com `Authorization: Bearer`, corpo `{"conversa_id": "<uuid>"}`.
- **200** `{"ticket": "<opaco>", "expira_em": 30}`: uso único, 30 s.
- **402**: o Cap não comporta a reserva de 9 min (ADR 0027).
- **404**: Conversa não existe ou é de outro Usuário.
- **409**: turno ativo na Conversa, ou o Usuário já tem Ligação ativa.
- **429**: teto global de 3 Ligações simultâneas.

## 2. Conexão
`wss://<host>/api/voz/ws?ticket=<ticket>`. O servidor valida o ticket e faz a reserva de crédito, a vaga de turno e a sessão Gemini. Então manda `{"tipo":"pronto"}`. Recusa depois do upgrade usa close code:
- `4401` ticket inválido, expirado ou já usado
- `4402` Cap
- `4409` turno ou Ligação ativa
- `4429` teto global
- `4500` falha ao abrir o Gemini

## 3. Browser → servidor
- **Binário:** áudio do microfone, PCM 16-bit little-endian, 16 kHz, mono, chunks de 20 a 40 ms.
- **Texto JSON:**
  - `{"tipo":"frame","jpeg":"<base64>"}`: um Frame, no máximo 1 por segundo.
  - `{"tipo":"tela","ativa":true|false}`: início ou fim do compartilhamento (vira Evento de auditoria).
  - `{"tipo":"desligar"}`.

## 4. Servidor → browser
- **Binário:** áudio do agente, PCM 16-bit little-endian, 24 kHz, mono.
- **Texto JSON:**
  - `{"tipo":"pronto","limite_s":540}`. Fps (1) e resolução (1280) são constantes do front.
  - `{"tipo":"transcricao","origem":"usuario"|"agente","texto":"...","final":true|false}`. Agente: texto **acumulado**; cada mensagem `final:false` traz a fala inteira até agora e substitui a anterior; o fim do turno manda a fala inteira com `final:true`. Usuário: uma mensagem só, `final:true`.
  - `{"tipo":"interrompido"}`: o usuário falou por cima; o browser esvazia a fila de áudio.
  - `{"tipo":"fim","motivo":"desligou"|"limite"|"erro"|"queda"}`: o servidor fecha em seguida com close code `1000`.
  - `{"tipo":"erro","mensagem":"..."}`: legível para o usuário.

## 5. Fim
Qualquer fim (desligar, limite de 9 min, queda do browser, queda do Gemini) passa pelo mesmo caminho no servidor: grava as falas, faz o acerto de crédito, emite `voice_call_ended` e libera a vaga de turno.
