# Latência da Ligação: onde o tempo vai

Ticket 83, 29/09/2026. Latência = do último chunk de microfone com sinal (pico > 500) até o primeiro chunk de áudio do agente chegando no browser. É a régua do smoke do 80 (`web/scripts/smoke-ligacao-prod.mjs`).

**Ambiente de todos os números:** cliente = Windows do Toneli, Brave, rede residencial, microfone falso tocando `spike/live/pergunta.wav` (SAPI pt-BR, 7,3 s) e tela falsa em canvas a 1 fps. Produção = `https://chat.toneli.dev.br`, VPS Oracle São Paulo `<ip-do-vps>`, app na 8010 atrás do nginx do host. Local = API do repo na porta 8083, Postgres 5433, mesma máquina do browser. Modelo `gemini-3.8-live`, chave free. Todo número abaixo é uma amostra pequena (n indicado), não uma média.

## Resposta curta
- **A rede não é a causa.** Cliente → VPS: 12 ms (TCP connect). VPS → Google: 2 ms (TCP), 56 ms (TLS). Ida e volta pelo proxy, browser ⇄ servidor: 40 a 50 ms. Reprodução: o chunk toca no mesmo instante em que chega (0 ms). O nginx não foi tocado.
- **A mesma medição rodada local dá 1,7 s**, igual à de produção (1,9 s). O "0,5 s local" dos tickets 75 e 76 usou outra régua (script direto, sem o browser); o script do 76 não foi commitado, a régua exata é INFERIDA.
- **O tempo está no Gemini, em duas partes:** (1) o VAD espera silêncio antes de fechar a fala; (2) o modelo pensa antes de falar. A parte (1) foi medida e reduzida. A parte (2) varia de 0,4 a 3,0 s e não tem alavanca de configuração no `gemini-3.8-live`.

## Tabela por salto

Marcos do servidor (`?trace=1`, relógio monotônico do servidor, log `trilha`). "Silêncio do mic" = primeiro chunk abaixo do pico 500 depois da fala. Tempos em ms.

| Salto | Local, antes (n=1) | Produção, depois (n=3) |
|---|---|---|
| Browser → servidor → Gemini + servidor → browser (soma dos dois trechos de rede) | ~30 | 39, 42, 51 |
| Silêncio do mic → `ACTIVITY_END` (VAD do Gemini fecha a fala) | **1292** | **823, 890, 926** |
| `ACTIVITY_END` → 1º áudio do Gemini (modelo, com pensamento) | 379 | **3037, 2416, 1334** |
| 1º áudio recebido → começa a tocar | 0 | 0 |
| **Total medido no browser** | **1703** | **3899, 3348, 2311** |

Antes em produção, do ticket 80 (sem trilha, só o total, 2 sessões): **1909** (leu a tela) e **3270** (sessão sem tela válida).

Pensamento do modelo por turno na sessão de produção (`thoughts_token_count` do `turn_complete`): 152, 161 e 108 tokens, na ordem das três perguntas. Os tempos do modelo (3037, 2416, 1334 ms) seguem a mesma ordem. INFERIDO: com n=3 é correlação, não prova.

## Causa
1. **VAD.** O Gemini só fecha a fala do usuário depois de um silêncio. O servidor usa o padrão dele (~800 ms, do guia do Gemini; o valor não está no SDK). Medido: 1292 ms entre o silêncio do microfone e o `ACTIVITY_END`. Isto é 75% dos 1,7 s da medição local.
2. **Pensamento do modelo.** Depois do `ACTIVITY_END`, o modelo gera pensamento (80 a 452 tokens por turno no spike 75) antes do primeiro som. Em produção pesou de 1,3 a 3,0 s. É a variância entre 1,9 s e 3,3 s do ticket 80.

## Fix
`api/app/voz.py` `_conectar`: `realtime_input_config.automatic_activity_detection` com `end_of_speech_sensitivity=HIGH` e `silence_duration_ms=500` (`settings.ligacao_silencio_ms`, variável `LIGACAO_SILENCIO_MS`). Efeito medido em produção: silêncio → `ACTIVITY_END` de 1292 para 823 a 926 ms, **ganho de ~400 ms** (n=1 antes, n=3 depois).

**Não melhorou o total.** O total em produção depois (2,3 a 3,9 s) ficou acima dos 1,9 e 3,3 s do 80, porque a parte do modelo pesou 1,3 a 3,0 s nessa sessão. Os 400 ms do VAD ficaram escondidos pela variância do modelo. Só com mais amostras dá para mostrar o ganho no total.

**Ressalvas do fix:**
- Foram mudados dois parâmetros juntos (sensibilidade e duração). O efeito é do par; não sei o quanto vem de cada.
- Risco: fala partida. Na 1ª pergunta da sessão de produção o VAD fechou a fala depois de 1 s de fala e abriu outra 313 ms depois (o WAV tem uma pausa de ~1 s depois da primeira palavra). O modelo respondeu só à segunda metade. Nas outras duas perguntas, com o mesmo WAV, não partiu. Com o padrão do servidor, na medição local, não partiu. Pausa natural de pessoa passa de 500 ms com frequência: o valor pode precisar subir para 700 ms se o uso real mostrar corte.
- O issue googleapis/python-genai#2580 diz que o `gemini-3.1-flash-live-preview` ignora `silence_duration_ms`. Para o `gemini-3.8-live` o ganho de 400 ms mostra que não ignora, mas isso vale para o par de parâmetros.

## Descartado, e como
| Hipótese do ticket | Resultado | Como |
|---|---|---|
| Fim da fala não sinalizado (nada chega depois do áudio) | Descartada | Sonda sem custo (`web/scripts/sonda-mic-falso.mjs`): depois do WAV o microfone falso segue mandando 235 chunks de silêncio digital (pico 0) por 7,5 s, sem buraco maior que 51 ms. O worklet não descarta chunk silencioso |
| Buffer no caminho (nginx, Nagle, fila de reprodução) | Descartada | Soma dos dois trechos de rede é 40 a 50 ms; o `proxy_buffering off` já é herdado pela location do WebSocket; chunk toca 0 ms depois de chegar |
| Trabalho síncrono no loop do relay | Descartada | O total do salto de rede inclui o relay (com a trilha ligada, que ainda calcula o pico de cada chunk): 40 a 50 ms |
| Distância VPS → Google | Descartada | 2 ms de TCP, 56 ms de TLS; da máquina local 8 a 43 ms de TCP, 70 ms de TLS |
| Frames competindo com o áudio | Não testada | Sem medição com e sem tela. As sessões tinham 1 Frame por segundo e a soma dos trechos de rede ficou em 40 a 50 ms, o que limita o efeito |
| Pensamento do modelo | Medido, sem alavanca | O guia do Gemini diz que o `gemini-3.8-live` não aceita `thinking_level` (só o `-extended-thinking` e o 3.1 aceitam). Enviar quebraria a conexão. `thinking_budget` não foi testado |

## Chamadas reais deste ticket
3 sessões Live na chave free, R$ 0: (1) local, caiu aos 22 s por defeito meu na trilha (`AttributeError`), deu o tempo até a transcrição; (2) local, sessão completa, o "antes"; (3) produção, 65 s, 3 perguntas, o "depois". Mais 1 conexão sem áudio para conferir que a config do VAD é aceita. Conta de teste em produção: `lat83-prod@example.com` (conversa da sessão 3: `852af629-7af4-4d2b-8ec3-f73892836963`).

## Como repetir
```
# Sonda sem custo do microfone falso
node web/scripts/sonda-mic-falso.mjs <wav-com-8s-de-silencio>
# Sessão real, com trilha no servidor e várias perguntas num WAV
SMOKE_EMAIL=... SMOKE_SENHA=... node web/scripts/smoke-ligacao-prod.mjs --wav <wav> --trace --fixo 62
# Trilha em produção
ssh ... "sudo docker logs tess-chat-app-1 | grep trilha"
```
A trilha só liga com `?trace=1` na URL do WebSocket. Loga tempos e o tipo do evento; nenhum áudio, texto ou dado do usuário. Sai em nível `warning` porque o app não configura o nível `info` do logger.

## Próximos passos, se a latência importar
1. Repetir a sessão de produção com 5 ou mais perguntas para separar o ganho do VAD da variância do modelo.
2. Testar `thinking_budget=0` numa conexão sem áudio para saber se o `gemini-3.8-live` aceita.
3. Subir `silence_duration_ms` para 700 se aparecer fala partida no uso real.
4. Sem `audio_stream_end` nem VAD no cliente: fica como está (troca de decisão do ADR 0026, não coube aqui).
