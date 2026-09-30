# Latência da Ligação: onde o tempo vai

Ticket 83, 29/09/2026. Latência = do último chunk de microfone com sinal (pico > 500) até o primeiro chunk de áudio do agente chegando no browser. É a régua do smoke do 80 (`web/scripts/smoke-ligacao-prod.mjs`).

**Ambiente de todos os números:** cliente = Windows do Toneli, Brave, rede residencial, microfone falso tocando `spike/live/pergunta.wav` (SAPI pt-BR, 7,3 s) e tela falsa em canvas a 1 fps. Produção = `https://chat.toneli.dev.br`, VPS `<ip-do-vps>`, app na 8010 atrás do nginx do host. Local = API do repo na porta 8083, Postgres 5433, mesma máquina do browser. Modelo `gemini-3.8-live`, chave free. Todo número abaixo é uma amostra pequena (n indicado), não uma média.

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
2. ~~Testar `thinking_budget=0`~~ Feito na rodada 2: aceito, zera o pensamento, não corta o tempo.
3. Subir `silence_duration_ms` para 700 se aparecer fala partida no uso real.
4. Sem `audio_stream_end` nem VAD no cliente: fica como está (troca de decisão do ADR 0026, não coube aqui).

## Rodada 2 (ticket 85): truques para cortar o tempo real e o percebido

29/09/2026. **Ambiente de todos os números da rodada:** produção `https://chat.toneli.dev.br` (VPS `<ip-do-vps>`, deploy do commit `8c2941a`), cliente Windows do Toneli, Brave, rede residencial, microfone falso tocando `.scratch/desafio/lat83/pergunta-x3.wav` (3 perguntas iguais, "leia o número do pedido e o total"), tela falsa em canvas a 1 fps, `--trace`, modelo `gemini-3.8-live` (exceto `m31`), chave free, conta `lat85-prod@example.com`. Tudo numa tarde, misturado no tempo. Log por marco em `.scratch/desafio/lat85/trilha-prod.txt`; a tabela sai de `.scratch/desafio/lat85/tabela.py`.

### Truques pesquisados, do maior ganho esperado ao menor
| # | Truque | O que é e por que deveria funcionar | Fonte | Testado? |
|---|---|---|---|---|
| 1 | **Menos pensamento** | O modelo pensa 100 a 450 tokens antes do 1º áudio. Ou se desliga o pensamento, ou se usa um modelo Live com nível `minimal`. | Guia Live do Gemini: `gemini-3.1-flash-live-preview` aceita `thinkingLevel` (`minimal` a `high`); `gemini-3.8-live` não aceita `thinkingLevel`. `thinking_budget` não está no guia; testei numa conexão e o 3.8 aceita. Docs do LiveKit: `minimal` é o padrão do 3.1, "para menor latência". | Sim: `pens0` e `m31` |
| 2 | **Menos contexto por Frame** | Cada Frame soma tokens ao contexto; contexto maior poderia atrasar o 1º token. O plugin Gemini do LiveKit manda 1 frame/s enquanto o usuário fala e 1 a cada 3 s fora da fala, e expõe `media_resolution` baixa. | Docs do LiveKit (plugin Gemini Live); guia Live (`mediaResolution`) | Sim, o corte de Frame (`fq`). `media_resolution` não |
| 3 | **Fim de fala fora do VAD do servidor** | Desligar o VAD automático e mandar `activity_start`/`activity_end` de um detector no cliente (Silero) ou semântico. Ataca os 0,75 a 1 s de VAD, que é metade do tempo. | Guia Live (`disabled`, `activityStart`, `activityEnd`); LiveKit desliga o VAD do Gemini para usar o turn detector dele | Não. Troca a decisão do ADR 0026 e não cabe em 8 sessões com n ≥ 3. Fica como próximo passo |
| 4 | **Latência percebida** | Quem espera em silêncio acha mais lento do que quem vê que o sistema ouviu. Um indicador "pensando" assim que a fala acaba mascara a espera. Não corta o tempo real. | Relatos de Pipecat e LiveKit: medir endpointing separado do pipeline, com meta de ~600 a 800 ms fim a fim para "parecer vivo" | Sim: indicador visual. Som local ("hmm") não |
| 5 | **Silêncio do VAD e `prefix_padding_ms`** | Menos silêncio, fim de fala mais cedo. Já está em 500 ms; `prefix_padding_ms` mexe no começo da fala, não no fim. | Guia Live | Não. Já no piso da faixa do guia (500 a 800 ms); o ganho restante é menor que o ruído |

Descartado sem gastar sessão: `audio_stream_end`. O guia diz que ele descarrega áudio em cache quando o microfone pausa. O nosso microfone nunca pausa: a sonda do 83 provou que o worklet manda chunk de silêncio o tempo todo.

### O que foi testado (6 sessões de 65 s + 12 conexões curtas de texto, chave free, R$ 0)
Antes das sessões: 12 conexões de texto (menos de 10 s cada) para saber se a config é aceita e se `thoughts_token_count` cai. `thinking_budget=0` no 3.8 é aceito e zera o pensamento. `gemini-3.1-flash-live-preview` com `thinking_level="minimal"` é aceito. Depois, no navegador, uma variante por vez, via `?v=` no WebSocket (`api/app/voz.py` `VARIANTES`): sem deploy por variante.

Métricas por pergunta. **Browser** = fim da fala até 1º chunk de áudio, régua do 83. **Modelo** = `ACTIVITY_END` até 1º áudio (trilha do servidor). **VAD** = último silêncio do microfone até `ACTIVITY_END`. Tempos em ms.

| Variante | Sessões / perguntas respondidas | Browser (por pergunta) | Mediana browser | Modelo (por pergunta) | Mediana modelo | VAD (por pergunta) | Pensamento (tokens, soma da sessão) | Leu a tela |
|---|---|---|---|---|---|---|---|---|
| **padrão** (3.8, VAD 500 ms) | 2 / 6 | 1779, 1449, 1657 · 2935, 1790, 1946 | **1785** | 975, 660, 859 · 1957, 866, 1166 | 920 | 765, 741, 746 · 933, 880, 729 | 306 · 364 | sim |
| `pens0` (`thinking_budget=0`) | 1 / 3 | 2448, 2092, 5094 | 2448 | 1403, 1275, 2114 | 1403 | 1008, 768, 2931 | **0** | sim |
| `m31` (3.1 flash live, `minimal`) | 2 / 5 de 6 | 1406, 1459 · 1341, 1498, 1389 | **1406** | 244, 423 · 247, 414, 417 | **414** | 1122, 996 · 1052, 1034, 933 | 0 | sim |
| `fq` (Frame só na fala) | 1 / 3 | 4073, 5834, 1833 | 4073 | 979, 898, 952 | 952 | 3052, 4884, 832 | 269 | sim |

O padrão desta tarde ficou entre 1,4 e 2,9 s, mais rápido que os 2,3 a 3,9 s de manhã (83), com a mesma config de VAD. A variação do Gemini entre horas passa de 1 s. INFERIDO: carga do lado do Google. Por isso os números só valem comparados dentro desta tarde, e são n pequeno.

### O que ficou, o que caiu
- **Ficou: indicador "pensando" no browser (truque 4).** Acende 409 a 419 ms depois do último chunk de fala (18 de 18 perguntas, medido por `MutationObserver` no DOM, `pensandoLigouAposFimFalaMs` do smoke) e apaga no 1º áudio. O usuário vê a reação em ~0,4 s e não em ~1,8 s de silêncio. **É mascaramento, não ganho de latência**; dizer isso no vídeo. Custo de código: 1 estado e 1 função no hook.
- **Ficou como opção, não como padrão: `?v=m31`.** Tira ~500 ms do tempo do modelo (mediana 920 → 414). O ganho líquido no browser é de ~380 ms (1785 → 1406), porque o 3.1 ignora `silence_duration_ms` (issue googleapis/python-genai#2580, confirmado: VAD de ~1,0 s contra 0,75 s). Contra: em 1 das 2 sessões ele não respondeu à 3ª pergunta (nem transcreveu; a trilha não mostra `ACTIVITY_START`), é modelo `preview`, e não tem linha na Tabela de Preço (o Ledger cobra ao preço do 3.8, INFERIDO igual). Virar padrão pede migração de preço e ADR novo. Não fiz.
- **Caiu: `thinking_budget=0` (`pens0`).** O pensamento zerou (0 tokens) e a latência não caiu: modelo 1403 ms de mediana contra 920, n=3 contra n=6. Não é prova de piora; é prova de que não ajuda. INFERIDO: o `gemini-3.8-live` faz raciocínio intercalado com perfil de latência fixo, e o orçamento só some com o custo dos tokens, não com o tempo.
- **Caiu: cortar Frame (`fq`).** Mandou 35 Frames em vez de 64 (-45%) e o tempo do modelo ficou igual (952 contra 920). A hipótese "o contexto cresce por Frame e o 1º token atrasa" também perde para os dados do padrão: o tempo do modelo não cresce da 1ª para a 3ª pergunta (975, 660, 859; 1957, 866, 1166) e no 83 ele até caiu (3037, 2416, 1334). O VAD longo de `fq` e `pens0` (3 a 4,9 s em 3 das 17 perguntas) é ruído do lado do Gemini, não efeito da variante: o `fq` da 3ª pergunta teve 832 ms.
- **Não feito: VAD no cliente (truque 3).** É o único que ataca os 0,75 a 1 s de VAD. Custa mudar o ADR 0026. Próximo passo, se a latência importar.
- **Ressalva:** com a mesma WAV, o VAD do Gemini às vezes leva 3 a 5 s para fechar a fala (3 de 17 perguntas nas 4 variantes). Isso passa de tudo que os truques mexem.

### Como repetir
`pens0` e `fq` saíram do código depois da medição (caíram); só `m31` segue em `VARIANTES`. Para repetir os dois, restaurar o commit `8c2941a`.
```
cd web
SMOKE_EMAIL=lat85-prod@example.com SMOKE_SENHA=<senha da conta> node scripts/smoke-ligacao-prod.mjs \
  --wav ../.scratch/desafio/lat83/pergunta-x3.wav --trace --fixo 62 --v m31   # sem --v = padrão
ssh -i <chave> <usuario>@<ip-do-vps> "sudo docker logs --since 3h tess-chat-app-1 2>&1 | grep trilha" > trilha.log
python ../.scratch/desafio/lat85/tabela.py trilha.log
```
