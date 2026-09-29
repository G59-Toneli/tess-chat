# 75 — Spike: Gemini Live com áudio, frame e transcrição

**Type:** spike (spike/)
**Status:** resolved
**Blocked by:** —
**Refs:** ADR 0026, 0027, 0028. Pesquisa de 28/09 (docs oficiais: ai.google.dev/gemini-api/docs/live, live-guide, live-session, ephemeral-tokens, pricing).

**Objetivo:** provar, antes de qualquer feature, que o caminho do ADR 0026 funciona e fixar os nomes reais do SDK. Agentes seguintes copiam daqui; não inventam config.

## Escopo
Script `spike/live/spike_live.py` (~40 a 80 linhas, `google-genai` que já está no `uv.lock`, rodado com `cd api && uv run python ../spike/live/spike_live.py`). Este ticket PODE tocar `spike/`.
1. Conecta em `gemini-3.8-live` com a chave free (`GEMINI_API_KEY` do `.env`). Se a free falhar no Live, repete com `GEMINI_PAID_API_KEY` e registra o erro exato.
2. Config: resposta em áudio, voz pt-BR (escolher uma, registrar o nome), `input_audio_transcription`, `output_audio_transcription`, context window compression ligada, system instruction curta.
3. Envia ~3 s de PCM 16 kHz (gerar com TTS local ou um WAV qualquer com fala; se não houver, silêncio + uma pergunta em texto) e 1 frame JPEG de uma tela com texto, a 1280 px e depois a 768 px.
4. Recebe: áudio (confirma 24 kHz PCM), transcrições de entrada e saída, `usageMetadata` (formato exato, por modalidade), e se existe sinal `interrupted` e `goAway`.
5. Pergunta sobre o texto do frame e registra se o modelo leu certo nas duas resoluções.

## Aceite
- `spike/live/RESULTADO.md` com: nome exato do modelo; qual chave funcionou; trecho de config que funcionou (nomes reais das classes/campos do SDK); formato das mensagens recebidas (áudio, transcrição, interrupted, turn_complete, goAway, usageMetadata); tokens por frame a 1280 e 768; se o modelo leu o texto em cada uma; latência do fim da fala ao primeiro áudio (medida local, declarar host); voz escolhida.
- Recomendação de resolução pela regra do ADR 0028 (>~1000 tokens/frame → 768).
- Se algo divergir dos ADRs 0026 a 0028, registrar no RESULTADO e em DECISOES-AUTONOMAS. Não editar os ADRs.
- Chamadas reais: teto 3 sessões (contam no teto de 10 da etapa). Registrar no LEDGER.

## Paradas de estudo
Ao terminar, adicione aqui 2 a 4 entradas no formato do `docs/ESTUDO-VOZ.md` (conceito, porquê, alternativa que caiu, `arquivo:linha`, pergunta de entrevista + resposta). Ex.: o que é PCM 16 kHz e por que 16 na entrada e 24 na saída.

### 1. PCM 16 kHz na entrada, 24 kHz na saída
- **Conceito:** PCM é áudio cru: uma amostra de 16 bits por instante, sem compressão. 16 kHz são 16 mil amostras por segundo, 32 KB/s em mono. A frequência de amostragem limita o agudo que o áudio carrega (metade dela).
- **Por quê:** voz humana inteligível cabe em 8 kHz de banda; 16 kHz de amostragem basta para o reconhecimento e é o que o Live exige na entrada. Na saída o Gemini gera 24 kHz para a voz soar natural. Opus ou MP3 cairiam: o Live não aceita, e codificar no browser soma latência.
- **Onde:** `spike/live/spike_live.py:33` (envio com `audio/pcm;rate=16000`); `spike/live/RESULTADO.md`, tabela de mensagens (`audio/pcm;rate=24000` confirmado).
- **Pergunta de entrevista:** "Por que o microfone manda 16 kHz e o alto-falante toca 24 kHz?"
  **Resposta:** Entrada é para a máquina entender; 16 kHz cobre a banda da fala e é o formato que o Live pede. Saída é para gente ouvir; 24 kHz soa mais natural. Mandar cru evita codec e latência de compressão.

### 2. Frame custa tokens fixos, não por pixel
- **Conceito:** cada imagem que entra no Gemini vira tokens. No Live, com `media_resolution` padrão, o Frame virou 264 tokens a 1280 e a 768.
- **Por quê:** o ADR 0028 previa baixar para 768 se o Frame passasse de ~1000 tokens. Medido: 264 nas duas. Fica 1280 porque a regra não disparou. Diferença de legibilidade entre as duas: INFERIDO, não testada (o texto de 16 pt leu nas duas). Se 264 é um bloco fixo, o servidor reduz a imagem para o mesmo tamanho interno; aí 768 lê igual com 40% dos bytes (15 KB contra 37 KB por Frame) e é a candidata se a banda pesar.
- **Onde:** `spike/live/spike_live.py:38` (1 fps); `spike/live/RESULTADO.md`, seção Tokens por Frame.
- **Pergunta de entrevista:** "Como você escolheu a resolução da captura de tela?"
  **Resposta:** Medi antes de decidir. Mandei o mesmo documento a 1280 e a 768 e li o `usageMetadata`: 264 tokens nas duas, e o modelo leu o texto nas duas. Custo igual, então fiquei com o que o ADR já dizia. Se a banda do WebSocket pesar, 768 é a troca barata, e é config.

### 3. `usage_metadata` por turno, e o pensamento fora do total
- **Conceito:** o Live manda o consumo junto do `turn_complete`, um por turno. O `prompt_token_count` é o contexto inteiro daquele turno, separado por modalidade (TEXT, AUDIO, IMAGE).
- **Por quê:** o acerto de crédito (ADR 0027) soma os turnos. Pegar só o último cobraria menos. `thoughts_token_count` não entra no `total_token_count`; o acerto precisa somar à parte.
- **Onde:** `spike/live/spike_live.py:64` (`anotar` loga cada mensagem); `spike/live/out/sessao3_1280.jsonl` (dois turnos).
- **Pergunta de entrevista:** "Como o servidor sabe quanto a Ligação custou?"
  **Resposta:** O Gemini reporta o uso por turno, por modalidade. O servidor soma e multiplica pelo preço de cada modalidade da Tabela de Preço. Sem o reporte (queda), estima por duração: ~25 tokens por segundo de áudio.

### 4. Barge-in: o sinal `interrupted`
- **Conceito:** o VAD do Gemini detecta que o usuário começou a falar enquanto o modelo responde. Ele manda `voice_activity` `ACTIVITY_START`, depois `server_content.interrupted = true` e um `turn_complete` do turno cortado.
- **Por quê:** o áudio já enviado ao browser continua na fila. Sem esvaziar a fila no `interrupted`, o agente segue falando por cima do usuário. VAD no cliente caiu: seria mais código e duas fontes de verdade.
- **Onde:** `spike/live/spike_live.py:46` (`microfone` repete a fala por cima com `--interromper`); `spike/live/out/sessao3_1280.jsonl`.
- **Pergunta de entrevista:** "O que acontece quando o usuário interrompe o agente?"
  **Resposta:** O Gemini percebe a voz nova e manda `interrupted`. O servidor repassa `{"tipo":"interrompido"}` e o browser joga fora o áudio que ainda não tocou. O modelo responde a fala nova no turno seguinte.

## Answer
Spike feito em `spike/live/` com 3 sessões Live reais, todas na chave free. `gemini-3.8-live`, voz `Kore` (pt-BR sem `language_code`), saída `audio/pcm;rate=24000`, `interrupted` observado, `go_away` só no SDK. Frame custa 264 tokens a 1280 e a 768: resolução fica 1280. O modelo leu o texto nas duas.
Ressalva: na sessão 1 o modelo negou ver a tela com a instrução "sem tela, diga que não vê nada"; a instrução nova (em `RESULTADO.md`) resolveu, causa não isolada. `usage_metadata` vem por turno e `thoughts_token_count` fica fora do total: o 76 soma e precisa de preço para pensamento.
Divergências dos ADRs 0026 a 0028 em `spike/live/RESULTADO.md` e `docs/DECISOES-AUTONOMAS.md`. Nada ficou `REVISAR(human)`.
