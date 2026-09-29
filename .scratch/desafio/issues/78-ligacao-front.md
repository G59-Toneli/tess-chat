# 78 — Painel de Ligação no front: microfone, alto-falante, tela

**Type:** task (web/)
**Status:** blocked
**Blocked by:** 75
**Refs:** ADR 0026, 0028. `docs/PROTOCOLO-LIGACAO.md` (contrato, obrigatório). `docs/UI-GUIA.md` (obrigatório). Pode correr em paralelo com o 76: o contrato é o protocolo.

**Objetivo:** uma Ligação estilo Discord dentro da Conversa.

## Escopo
Componentes novos `web/src/components/Ligacao*.tsx` e `web/src/lib/ligacao/*`. Em `Chat.tsx`, só o botão e o encaixe do painel.
1. **Botão de telefone no cabeçalho da Conversa** abre o painel sobre o chat. Estados: conectando, em ligação, encerrando, erro (402, 409, 429 e close codes com mensagem legível).
2. **Captura:** `getUserMedia` com `echoCancellation`, `noiseSuppression`, `autoGainControl`. `AudioWorklet` converte para PCM16 16 kHz mono e manda chunks de 20 a 40 ms.
3. **Reprodução:** PCM16 24 kHz numa fila de `AudioContext`. No `interrompido`, esvazia a fila na hora.
4. **Tela:** botão compartilhar/parar. `getDisplayMedia`, desenha num canvas a 1 fps, JPEG 0,7, lado maior 1280 (valores do `/pronto` ou constantes de config). Prévia pequena da tela no painel. `track.onended` (barra do browser) para os frames e manda `tela` `false`. Sem `getDisplayMedia` (celular), o botão some.
5. **Controles:** mutar microfone, desligar, contador de tempo com o limite. Transcrição ao vivo (usuário e agente).
6. **Input de texto desabilitado** durante a Ligação.
7. Desmontar a tela ou fechar a aba encerra microfone, tela e WebSocket.

## Aceite
- `npm run build` e `tsc` limpos; `checar-responsivo.mjs` sem violação nova.
- Teste contra um servidor WS falso local que segue o protocolo (script em `web/scripts/` ou no teste): o áudio sai binário, o frame sai em 1 fps, `interrompido` esvazia a fila.
- Screenshots no Brave (dark, 1440x900) em `.scratch/desafio/screens/78-*`: painel conectando, em ligação com prévia de tela e transcrição, erro 402.
- `REVISAR(human)` no worklet de captura, na fila de reprodução e no laço de frames.
- Chamadas reais: 0 (o 80 faz o ponta a ponta).

## Paradas de estudo
3 a 5 entradas no formato do `docs/ESTUDO-VOZ.md`. Obrigatórias: por que AudioWorklet e não MediaRecorder; como o barge-in funciona no browser; por que 1 fps basta.
