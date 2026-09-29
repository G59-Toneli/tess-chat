# 75 — Spike: Gemini Live com áudio, frame e transcrição

**Type:** spike (spike/)
**Status:** ready-for-agent
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
