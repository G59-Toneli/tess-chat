# 80 — Ligação ponta a ponta: E2E com mídia falsa e smoke real em produção

**Type:** task (web/ + api/)
**Status:** blocked
**Blocked by:** 76, 78, 79
**Refs:** ADR 0026 a 0028, `docs/PROTOCOLO-LIGACAO.md`.

**Objetivo:** provar que a Ligação funciona inteira, primeiro de graça, depois de verdade.

## Escopo
1. **E2E sem custo:** Playwright com Chromium e `--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` (microfone e tela falsos), contra a API local com o Gemini falso do 76. Fluxo: abrir Conversa, ligar, compartilhar tela, receber áudio e transcrição, desligar, ver as falas no histórico (se o 77 estiver resolvido), ver `voice_call_ended` em `/auditoria`.
2. **Smoke real em produção:** 2 a 3 Ligações de até 2 min no Brave, em `chat.toneli.dev.br`, com uma aba com texto compartilhada. Perguntar sobre o texto. Medir a latência do fim da fala ao primeiro áudio (declarar host e rede). Conferir o Ledger e a auditoria.
3. Defeito achado: corrigir se for pequeno, senão abrir ticket de ajuste.

## Aceite
- E2E verde, script commitado.
- Smoke: resultado, latência medida e chamadas no LEDGER. Screenshot em `.scratch/desafio/screens/80-*`.
- Chamadas reais: teto 3 sessões de até 2 min (dentro do teto de 10 da etapa).

## Paradas de estudo
1 a 2 entradas no formato do `docs/ESTUDO-VOZ.md`: como testar áudio e tela sem microfone de verdade.
