# ADR 0026 — Ligação por Gemini Live com proxy WebSocket no backend

**Status:** aceito, 2026-09-28. Estende o ADR 0001: a Ligação usa o SDK `google-genai` direto, porque o Pydantic AI não tem abstração para a Live API. O ADR 0018 continua valendo: só Gemini.

## Contexto
Nova etapa do desafio (prazo 30/09 23h59): conversa por voz com o agente e compartilhamento de tela durante a ligação. O agente vê a tela e responde sobre ela. Custo de API perto de zero. Pesquisa de 28/09: o `gemini-3.8-live` aceita áudio e imagem na mesma sessão, responde em áudio, transcreve as duas falas e tem free tier. Sem context window compression, uma sessão com vídeo morre em 2 min; a conexão cai em ~10 min. O Brave bloqueia o `SpeechRecognition` do browser.

## Decisão
Toneli, 28/09 (grilling):
1. **Modelo:** `gemini-3.8-live` (nome confirmado pelo spike, ticket 75). O `-extended-thinking` pensa antes de falar: latência na fala.
2. **Transporte: proxy.** Browser ⇄ WebSocket no FastAPI ⇄ Gemini Live. O servidor é dono da sessão; o browser é microfone, alto-falante e câmera da tela.
3. **Autenticação do WebSocket por ticket.** `POST /api/voz/ticket` (Bearer normal) devolve um código de uso único que vale 30 s. O WebSocket conecta com `?ticket=`. O browser não manda header em WebSocket, e o JWT na URL ficaria 24 h no log do nginx.
4. **A Ligação é um turno longo.** Ela ocupa a vaga de turno da Conversa (`turnos.reservar`, ADR 0023). Texto durante a Ligação recebe o mesmo 409. A UI desabilita o input.
5. **Compressão de contexto ligada e Ligação limitada a 9 min.** Sem session resumption no MVP.
6. **Sem tools e sem Roteador na Ligação.** O Jev força a tool no passo 1 de um turno requisição/resposta; a Ligação é fluxo contínuo, e um roteador na frente atrasa a fala.
7. **Detecção de voz automática do Gemini (barge-in).** O usuário interrompe falando por cima; no sinal `interrupted`, o browser esvazia a fila de áudio. Microfone com `echoCancellation`.
8. **Prompt:** o system prompt do chat mais um adendo de voz (respostas curtas e faladas, sem markdown; sem tela, dizer que não vê nada).
9. **Voz fixa**, uma que fale pt-BR.
10. **Chave:** `GEMINI_LIVE_API_KEY`, apontando para a chave free. Se a free não servir no Live, usa a paga. Trocar a chave não muda código.
11. **Concorrência:** uma Ligação por Usuário, teto global de 3.
12. **Seam de teste:** a conexão com o Gemini fica atrás de `conectar_gemini()`, injetável como o modelo do chat. Os testes usam um Gemini falso.

### Alternativas descartadas
- **Browser direto no Gemini com token efêmero.** Menos código e um salto a menos. Mas o servidor fica cego: Cap e auditoria dependeriam do consumo que o browser reporta, e o browser pode mentir. O Cap (ADR 0004) e a auditoria (ADR 0007) são obrigatórios.
- **SSE.** Só vai do servidor para o cliente. O microfone precisa do caminho inverso, contínuo.
- **WebRTC (LiveKit, Pipecat).** Melhor em rede ruim (UDP, jitter buffer). Mas o Gemini Live fala WebSocket; WebRTC exige servidor de mídia e um worker novo. Não cabe no prazo.
- **Cascata STT → LLM → TTS (Groq Whisper, speechSynthesis).** Três peças para costurar, latência pior, e o reconhecimento do browser não funciona no Brave.
- **OpenAI Realtime.** 3 a 4 vezes mais cara, sem tela em stream, e quebraria o ADR 0018.
- **Session resumption.** Reconecta com um handle quando o Gemini derruba a conexão. É o próximo passo; a demo não tem Ligação de 10 min.

## Consequências
- Salto extra browser → VPS: dezenas de ms (INFERIDO, medir). O modelo leva centenas de ms para falar.
- O nginx do host precisa repassar o upgrade de WebSocket na rota da Ligação (ticket 79).
- Restart ou deploy no meio derruba a Ligação, como o turno do ADR 0023.
- Escalar para mais de um processo exige mover a sessão para um worker. YAGNI.
- No free tier, o Google usa o conteúdo (voz e tela) para treinar. Aceito para uma demo.
