# Spike 75: Gemini Live com áudio, Frame e transcrição

Execução: 2026-09-28 23:15 a 23:19 (-03). Host: máquina local do Toneli, Windows 11, rede de casa (tipo de link INFERIDO). Python 3.14 via `uv` do `api/`, `google-genai` 2.25.0 (`api/uv.lock`).
Script: `spike/live/spike_live.py`. Insumos: `spike/live/gen_assets.ps1` gera `pergunta.wav` (SAPI "Microsoft Maria", pt-BR, 16 kHz, 7,3 s) e `tela_1280.jpg` / `tela_768.jpg` (pedido de compra com texto, JPEG qualidade 70).
Evidência bruta: `spike/live/out/sessao{1,2,3}_*.jsonl` (uma mensagem por linha; bytes de áudio trocados pelo tamanho).

## Resumo

| Item | Resultado |
|---|---|
| Modelo | `gemini-3.8-live` (aceito como está, sem prefixo `models/`) |
| Chave | `GEMINI_API_KEY` (free) funcionou nas 3 sessões. A paga não foi usada. |
| Voz | `Kore`. Falou pt-BR sem `language_code`: o idioma vem da system instruction e da fala do usuário. |
| Áudio de saída | `inline_data.mime_type == "audio/pcm;rate=24000"` confirmado na mensagem |
| Tokens por Frame | **264 a 1280x720 e 264 a 768x432** (`media_resolution` não definido) |
| Leitura do texto | 1280: leu certo (sessão 3). 768: leu certo (sessão 2). Resposta: "O número do pedido é 4827-B e o valor total é R$ 1.350,90." |
| Latência fim da fala → primeiro áudio | 918 ms (s1), 522 ms (s2), 426 ms (s3). Medida do último chunk de fala enviado até o primeiro `inline_data`. O script mandou o áudio a ~0,7x do tempo real (`asyncio.sleep(0.032)` no Windows passa do alvo). Latência com microfone real: INFERIDO na mesma faixa. A primeira transcrição de saída chega junto. |
| `interrupted` | Existe. Observado na sessão 3. |
| `go_away` | Existe no SDK. Não observado (sessões de 20 a 37 s). |
| Recomendação de resolução | **1280.** 264 tokens < ~1000 (regra do ADR 0028), e o custo é o mesmo a 768. Legibilidade igual nas duas com texto de 16 pt; texto menor não testado. 768 é a troca se a banda do WebSocket pesar. |

## Sessões

| # | Resolução | Frames | System instruction | Leu a tela? | Uso (prompt TEXT/AUDIO/IMAGE, resposta AUDIO, thoughts) |
|---|---|---|---|---|---|
| 1 | 1280 | 1, antes da fala | "... Sem tela compartilhada, diga que não vê nada." | **Não.** "Eu não tenho acesso à sua tela, por isso não consigo ler as informações." | 443/330/264, 119, 452 |
| 2 | 768 | 12, a 1 fps até o fim da fala | "... Quando o usuário compartilha a tela, você recebe imagens dela e pode descrevê-las. Se não chegou nenhuma imagem, diga que não vê nada." | Sim | 464/330/264, 215, 84 |
| 3 | 1280 | 12, a 1 fps; fala repetida por cima da resposta | igual à 2 | Sim, nos dois turnos | turno 1: 464/330/264, 195, 87. Turno 2: 494/547/264, 218, 80 |

Sessão 1 falhou com o Frame no contexto (IMAGE = 264). A sessão 2 mudou duas coisas ao mesmo tempo (instrução e 1 fps). A causa não está isolada. INFERIDO: a frase "sem tela, diga que não vê nada" puxa a recusa. O ticket 76 usa a instrução da sessão 2 no adendo de voz e manda Frames a 1 fps, como o ADR 0028.

## Config que funcionou (nomes reais do SDK 2.25.0)

`spike_live.py:18`:

```python
types.LiveConnectConfig(
    response_modalities=[types.Modality.AUDIO],
    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore"))),
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
    system_instruction="...",
)
async with genai.Client(api_key=chave).aio.live.connect(model="gemini-3.8-live", config=config) as s: ...
```

- `api_version` padrão do cliente (sem `http_options`). `v1alpha` só é exigido para token efêmero, que o ADR 0026 descartou.
- `trigger_tokens` e `SlidingWindow.target_tokens` ficaram no padrão do servidor.
- `media_resolution` e `thinking_config` não definidos. O `gemini-3.8-live` base também pensa (`thoughts_token_count` de 80 a 452); o ADR 0026 atribuía o pensamento só ao `-extended-thinking`. O live-guide mostra `thinking_config=types.ThinkingConfig(thinking_level="low")` como alavanca de latência. Não testado.
- Envio: `s.send_realtime_input(audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000"))` em chunks de 1024 bytes (32 ms). Frame: `s.send_realtime_input(video=types.Blob(data=jpeg, mime_type="image/jpeg"))`.
- Microfone aberto: depois da fala o script manda silêncio (zeros) sem parar. O VAD automático fecha a fala sozinho. `audio_stream_end` não foi usado.
- Recepção: `async for m in s.receive()` termina a cada `turn_complete`. Para o turno seguinte, chamar `s.receive()` de novo num laço.

## Formato das mensagens recebidas (`types.LiveServerMessage`)

Ordem de uma resposta, com um campo preenchido por mensagem:

| Campo | Exemplo (`model_dump(exclude_none=True)`) | Quando |
|---|---|---|
| `session_resumption_update` | `{"new_handle": "1340d1ec-...", "resumable": true}` | ~1,2 s depois de conectar. Chega mesmo sem `session_resumption` na config. |
| `voice_activity` | `{"voice_activity_type": "ACTIVITY_START", "audio_offset": "0.240s"}` | VAD viu fala começar. `ACTIVITY_END` no fim. |
| `server_content.input_transcription` | `{"text": "Leia para mim o número do pedido ..."}` | Uma mensagem só, no fim da fala. Sem `finished`. |
| `server_content.model_turn.parts[].inline_data` | `{"data": <bytes>, "mime_type": "audio/pcm;rate=24000"}`, `role: "model"` | Chunks de 7 a 29 KB (0,15 a 0,6 s de áudio). |
| `server_content.output_transcription` | `{"text": "pedido é 4827-B"}` | Pedaços. Às vezes na mesma mensagem do áudio, às vezes separado. Sem `finished`. |
| `server_content.generation_complete` | `true` | O modelo terminou de gerar. O áudio pode ainda estar tocando no cliente. |
| `server_content.interrupted` | `true` | Logo depois de um `voice_activity` `ACTIVITY_START` durante a resposta. Seguido de `turn_complete` com o uso do turno cortado. |
| `server_content.turn_complete` + `usage_metadata` | ver abaixo | **Na mesma mensagem.** 3 a 7 s depois de `generation_complete`. |
| `go_away` | `LiveServerGoAway.time_left: str` (SDK) | Não observado. |
| (vazia) | `{}` depois do dump | 40% das mensagens. O SDK 2.25 não reconhece o campo. INFERIDO: tipo novo do servidor. O 76 ignora. |

`usage_metadata` (`types.UsageMetadata`), sessão 3, turno 2:

```json
{"prompt_token_count": 1378, "response_token_count": 218, "thoughts_token_count": 80, "total_token_count": 1596,
 "prompt_tokens_details": [{"modality": "TEXT", "token_count": 494}, {"modality": "AUDIO", "token_count": 547}, {"modality": "IMAGE", "token_count": 264}],
 "response_tokens_details": [{"modality": "AUDIO", "token_count": 218}]}
```

- **Um `usage_metadata` por turno, não um por sessão.** O `prompt_token_count` de cada turno é o contexto inteiro no momento do turno: no turno 2 o AUDIO foi de 330 para 547 (fala antiga + fala nova). O 76 **soma** os `usage_metadata` de todos os turnos. INFERIDO: cada turno cobra o contexto de novo, como no chat de texto.
- `total_token_count = prompt + response`. **`thoughts_token_count` fica fora do total.** A Tabela de Preço do ADR 0027 não tem linha para pensamento. INFERIDO: cobrar como texto de saída (US$ 4,50/1M).
- `response_tokens_details` só tem AUDIO. A transcrição de saída não aparece como TEXT.
- TEXT de ~450 tokens com uma system instruction de ~40. INFERIDO: prompt interno do modelo de voz mais as transcrições.

## Tokens por Frame

- IMAGE = 264 nas três sessões: 1 Frame (s1), 12 Frames iguais (s2, s3), 1280 ou 768. O número não muda com a resolução. Com `media_resolution` padrão, cada imagem vira um bloco fixo (~258 tokens, INFERIDO).
- 12 Frames enviados contaram como 264, não 12 x 264. INFERIDO: o contexto guarda só o Frame mais recente, ou o servidor descarta Frame igual. Com a tela mudando, o número pode subir. O acerto do 76 usa o IMAGE que o Gemini reporta, não uma conta por Frame.
- Custo por Frame a preço de tabela: 264 x US$ 1/1M = US$ 0,00026.

## Áudio: tokens por segundo (estimativa por duração do ADR 0027)

- Saída: 119 tokens em 4,5 s; 215 em 8,4 s. **~25 tokens/s.**
- Entrada: 330 tokens para 7,3 s de fala mais o silêncio até o fim do VAD. Com ~25 tokens/s dá ~13 s de áudio contado. INFERIDO: o silêncio do microfone aberto também conta.
- Fallback do acerto sem `usage_metadata`: 25 tokens/s de entrada durante toda a Ligação e 25 tokens/s de saída durante o tempo de fala do agente.

## Divergências dos ADRs (também em `docs/DECISOES-AUTONOMAS.md`)

1. **ADR 0028, premissa:** "o Gemini 3.x divide imagem grande em pedaços, e cada pedaço custa tokens". Não vale no Live com `media_resolution` padrão: 264 tokens a 1280 e a 768. A regra de ajuste (768 se > 1000) não dispara. A resolução passa a pesar só no tamanho do WebSocket (37 KB contra 15 KB por Frame) e talvez na legibilidade. INFERIDO: 264 é um bloco fixo, o servidor reduz a imagem para o mesmo tamanho interno, e 768 lê igual.
2. **ADR 0028, custo:** "~US$ 0,002/min de imagem". Com 264 tokens por Frame e cada Frame contado, 1 fps custaria US$ 0,016/min. O observado foi 264 por turno com tela parada. O número real fica entre os dois.
3. **ADR 0026 item 8, adendo de voz:** "sem tela, dizer que não vê nada" escrito como regra solta fez o modelo negar a tela que tinha. O adendo precisa dizer primeiro que as imagens da tela chegam.
4. **ADR 0026 item 10:** `GEMINI_LIVE_API_KEY` não existe no `.env`. O spike leu `GEMINI_API_KEY`. O 76 cria a variável.
5. **ADR 0027:** o `usage_metadata` vem por turno e com `thoughts_token_count` fora do total. O acerto soma os turnos e precisa de preço para pensamento.

## Chamadas reais

3 sessões Live com a chave free (s1 1280 23:15:53, s2 768 23:17:13, s3 1280 com interrupção 23:18:06). 0 chamadas pagas. Custo real: R$ 0. A preço de tabela: menos de US$ 0,01 no total.
