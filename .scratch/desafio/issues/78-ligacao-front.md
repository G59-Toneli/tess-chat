# 78 — Painel de Ligação no front: microfone, alto-falante, tela

**Type:** task (web/)
**Status:** resolved
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

### 1. AudioWorklet no microfone, não MediaRecorder
- **Conceito:** AudioWorklet é um pedaço de JS que roda na thread de áudio do browser e recebe as amostras cruas, 128 por vez. O nosso converte float para PCM16 e junta 512 amostras (32 ms a 16 kHz) num chunk.
- **Por quê:** o Gemini Live quer PCM16 cru a 16 kHz. O MediaRecorder só entrega áudio comprimido (Opus em WebM), em pedaços do tamanho que ele escolhe; o servidor teria que decodificar. O ScriptProcessorNode faria o mesmo que o worklet, mas é obsoleto e roda na thread principal, que trava quando o React renderiza.
- **Onde:** `web/src/lib/ligacao/captura.worklet.js:9`, `web/src/lib/ligacao/captura.ts:12`.
- **Pergunta de entrevista:** "Por que você não usou o MediaRecorder para mandar o áudio?"
  **Resposta:** Porque ele entrega Opus comprimido e o Gemini Live pede PCM cru. O AudioWorklet me dá as amostras cruas em tempo real, fora da thread do React. O AudioContext roda a 16 kHz, então o browser reamostra e o worklet só converte para int16 e junta em chunks de 32 ms.

### 2. Barge-in no browser
- **Conceito:** barge-in é o usuário falar por cima do agente e o agente parar. Quem detecta a fala é o VAD do Gemini. Ele manda `interrupted`, o servidor repassa `interrompido`, e o browser para o áudio que já está na fila.
- **Por quê:** o Gemini manda o áudio em rajada, mais rápido que o tempo real. Quando o usuário interrompe, o browser já tem segundos de fala agendados. Sem esvaziar a fila, o agente seguiria falando por cima. Cada chunk é um `AudioBufferSourceNode` agendado; esvaziar é chamar `stop()` em todos e zerar o próximo início.
- **Onde:** `web/src/lib/ligacao/reproducao.ts:43`, `web/src/lib/ligacao/useLigacao.ts:123`.
- **Pergunta de entrevista:** "Como o agente para de falar quando o usuário interrompe?"
  **Resposta:** O Gemini detecta a voz e manda `interrupted`; o backend repassa como `interrompido`. No browser, a fila de reprodução guarda cada chunk agendado e para todos na hora. O `echoCancellation` do microfone evita que a voz do próprio agente dispare o barge-in.

### 3. Por que 1 fps de tela basta
- **Conceito:** a tela vai como Frames JPEG, um por segundo, lado maior 1280, qualidade 0,7. O modelo não assiste vídeo: cada Frame vira uma imagem que ele lê.
- **Por quê:** o caso de uso é documento, código, slide e página, que mudam pouco por segundo. A Live API não aceita mais que 1 fps. O spike mediu 264 tokens por Frame a 1280 e a 768, então 1280 não custa mais. Movimento rápido (vídeo, jogo) fica fora, como diz o ADR 0028.
- **Onde:** `web/src/lib/ligacao/tela.ts:18`, `web/src/lib/ligacao/config.ts`.
- **Pergunta de entrevista:** "Por que não mandar a tela como vídeo?"
  **Resposta:** Porque o modelo lê imagens, não assiste vídeo, e a API aceita no máximo 1 imagem por segundo. Para documento e código, um quadro por segundo pega o que muda. O pior caso é o agente ver a tela de até 1 s atrás.

### 4. Microfone antes do ticket
- **Conceito:** ao clicar em ligar, o browser pede o microfone primeiro. Só depois pede o Ticket de Ligação e abre o WebSocket.
- **Por quê:** o Ticket vale 30 s e uma vez só. O pedido de permissão do microfone pode levar mais que isso. Na ordem inversa, o ticket morreria na tela de permissão, e a recusa do microfone gastaria um ticket à toa.
- **Onde:** `web/src/lib/ligacao/useLigacao.ts:84`.
- **Pergunta de entrevista:** "O que acontece se o usuário demora para liberar o microfone?"
  **Resposta:** Nada quebra, porque o ticket só é pedido depois da permissão. Se ele nega, a tela mostra o erro e nenhum ticket foi gasto.

### 5. Testar áudio e tela sem microfone de verdade
- **Conceito:** o teste roda o front real no Brave, com o microfone falso do browser (`--use-fake-device-for-media-stream`) e um canvas no lugar da tela. Um servidor falso fala o protocolo e grava o que chega.
- **Por quê:** o que importa é o que o servidor vê e o que o usuário vê: chunks binários de 1024 bytes, Frames a cada ~1000 ms com 1280x720, `tela` `false` quando a trilha acaba, fila vazia logo depois do `interrompido`. Chamar o Gemini de verdade custaria dinheiro e não seria repetível.
- **Onde:** `web/scripts/testar-ligacao.mjs`.
- **Pergunta de entrevista:** "Como você testou a Ligação sem gastar crédito?"
  **Resposta:** Com um servidor WebSocket falso que segue o protocolo e o Brave com mídia falsa. O teste afirma o que sai do browser (formato do áudio, ritmo dos Frames) e o que o usuário vê (fila esvazia, painel fecha, erro legível).

## Answer
Painel de Ligação no topo da Conversa (`LigacaoPainel.tsx`) com `lib/ligacao/*`: microfone por AudioWorklet (PCM16 16 kHz, 32 ms), fila de reprodução 24 kHz com barge-in, Frames 1 fps JPEG 0,7 lado 1280 com prévia, mudo, contador com limite, transcrição ao vivo, input travado durante a Ligação, erros 402/404/409/429 e 4401/4402/4409/4429/4500 em pt-BR. Botão "Ligar" numa linha nova no topo da coluna do chat (o header é do `AppLayout`, fora do escopo).
Teste: `web/scripts/testar-ligacao.mjs` (servidor falso na 8078, vite preview na 4188, Brave headless), 31 checagens passando. `npm run build` limpo; `checar-responsivo` sem violação em `/c/:id` e `/`.
Ressalvas: `transcricao.texto` tratado como acumulado, como o `voz.py` do 76 manda (o protocolo não diz; vale uma linha lá); o histórico não recarrega ao fim da Ligação (ticket 77); aba escondida por mais de 5 min pode espaçar o laço de Frames.
REVISAR(human): `captura.worklet.js` (worklet), `reproducao.ts` (fila), `tela.ts` (laço de Frames).
