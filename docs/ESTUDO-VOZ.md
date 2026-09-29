# Estudo da Ligação (voz + tela)

Roteiro de estudo do Toneli. Ordem de leitura: do clique no botão de telefone até o débito no Ledger.

O foco é o mecanismo: o que trafega em cada byte e em cada mensagem, quem chama quem, onde o crédito é reservado e onde é acertado. Decisão sem mecanismo não segura entrevista.

Fontes: ADR 0026, 0027 e 0028. Contrato browser ⇄ servidor em `docs/PROTOCOLO-LIGACAO.md`. Servidor ⇄ Gemini em `spike/live/RESULTADO.md`. Decisões dos agentes em `docs/DECISOES-AUTONOMAS.md`. Todo `arquivo:linha` abaixo foi conferido no código em 29/09/2026.

Marca **INFERIDO**: ninguém mediu nem leu na documentação. Fala assim na entrevista, sem esconder.

## Os números para saber de cabeça

Ambiente de cada número vem junto. Número sem ambiente não vale.

| Número | Valor | Ambiente |
|---|---|---|
| Microfone → servidor | 1024 bytes a cada 32 ms (512 amostras × 2 bytes), 32 KB/s | PCM16, 16 kHz, mono |
| Servidor → alto-falante | 48 KB/s de áudio, em chunks de 7 a 29 KB | PCM16, 24 kHz, mono; o Gemini manda em rajada, mais rápido que o tempo real |
| Frame da tela | 1 por segundo, JPEG qualidade 0,7, lado maior 1280 px, ~37 KB (1280) ou ~15 KB (768) | base64 no JSON deixa ~33% maior |
| Tokens por Frame | **264, igual a 1280 e a 768** | spike 75, `media_resolution` padrão. A premissa do ADR 0028 ("imagem grande vira pedaços") não vale no Live |
| Áudio em tokens | ~25 tokens por segundo, entrada e saída | spike 75 |
| Reserva de 9 min | **US$ 0,345** (não os ~US$ 0,25 do ADR 0027) | 25 t/s de áudio in e out + 264 tokens × 1 Frame/s, ao preço de tabela |
| Pensamento | 80 a 452 tokens por turno, **fora** do `total_token_count`; cobrado como saída de texto (US$ 4,50/1M) | INFERIDO. O modelo base também pensa, não só o `-extended-thinking` |
| Latência (fim da fala → 1º áudio) | **0,5 a 0,6 s local** (503 e 626 ms); spike 426 a 918 ms | Windows do Toneli, servidor na própria máquina |
| Latência em produção | **1,9 s** (sessão que leu a tela); 3,3 s na sessão sem tela | medida no browser, rede residencial → VPS `<ip-do-vps>`. Causa da diferença não isolada, INFERIDO |
| Custo real de uma Ligação | ~US$ 0,006 por minuto a preço de tabela (6012 micro-USD em 63 s); R$ 0 na chave free | smoke 80, produção |

## O caminho completo, em sequência

```
Browser (React)               Servidor (FastAPI, api/app/voz.py)          Gemini Live
     |                                    |                                    |
 1.  | getUserMedia (mic) + worklet       |                                    |
     |----- POST /api/voz/ticket -------->|  criar_ticket (voz.py:239)          |
     |      Bearer + {conversa_id}        |  _vaga: 409/429                    |
     |                                    |  _reservar: caber() -> 402?        |  (nada é gravado)
     |<---- 200 {ticket, expira_em:30} ---|  TICKETS[codigo] (memória, 30 s)   |
 2.  |                                    |                                    |
     |==== WS /api/voz/ws?ticket=... ====>|  accept                            |
     |                                    |  _consumir: pop do ticket, 4401?   |
     |                                    |  _vaga, turnos.reservar(cid)       |
     |                                    |  _reservar de novo, histórico      |
     |                                    |----- connect(model, config) ------>|
     |                                    |  audit voice_call_started          |
     |<---- {"tipo":"pronto"} ------------|                                    |
 3.  |                                    |                                    |
     |--- binário: 1024 B (PCM 16 kHz) -->|--- send_realtime_input(audio) ---->|
     |--- {"tipo":"frame","jpeg":...} --->|--- send_realtime_input(video) ---->|
     |--- {"tipo":"tela","ativa":true} -->|  audit screen_share_started        |
     |                                    |<-- input_transcription ------------|
     |<-- {"transcricao","usuario"} ------|                                    |
     |                                    |<-- inline_data (PCM 24 kHz) -------|
     |<-- binário (PCM 24 kHz) -----------|<-- output_transcription -----------|
     |<-- {"transcricao","agente",...} ---|                                    |
     |                                    |<-- turn_complete + usage_metadata -|  (soma no `lig.uso`)
 4.  |--- {"tipo":"desligar"} ----------->|  _relay acaba -> finally           |
     |                                    |  _encerrar: gravar_falas           |
     |                                    |             _acertar -> Ledger     |
     |                                    |             audit voice_call_ended |
     |                                    |             _liberar (vaga)        |
     |<---- {"tipo":"fim"} + close 1000 --|                                    |
 5.  | recarrega o histórico              |                                    |
```

## Formato de cada parada

### N. título
- **Conceito:** o que é, em 2 ou 3 frases simples.
- **Por quê:** a escolha feita e a alternativa que caiu.
- **Onde:** `arquivo:linha`.
- **Pergunta de entrevista:** "..." **Resposta:** o que o Toneli fala.

## Paradas

### 1. Microfone antes do ticket
- **Conceito:** ao clicar em Ligar, o browser pede permissão do microfone primeiro. Só depois pede o Ticket de Ligação e abre o WebSocket. O painel (`LigacaoPainel`) só existe na tela enquanto a Ligação existe, e é ele que monta o hook `useLigacao`. Desmontar o painel encerra microfone, tela e WebSocket. `Chat.tsx:347` faz essa montagem.
- **Por quê:** o Ticket vale 30 s e uma vez só. A tela de permissão pode levar mais que isso. Na ordem inversa o Ticket morreria esperando o clique, e uma recusa do microfone gastaria um Ticket à toa (e uma checagem de Cap).
- **Onde:** `web/src/lib/ligacao/useLigacao.ts:83` (`abrir`), `:87` (`abrirMicrofone`), `:99` (`pedirTicket`), `:105` (`new WebSocket`).
- **Pergunta de entrevista:** "O que acontece se o usuário demora para liberar o microfone?"
  **Resposta:** Nada quebra. O ticket só é pedido depois da permissão. Se ele nega, aparece o erro e nenhum ticket foi gasto.

### 2. Do microfone ao byte: AudioWorklet e PCM 16 kHz
- **Conceito:** o microfone entrega números decimais entre -1 e 1 (float). O Gemini Live quer PCM16: um inteiro de 16 bits por amostra, sem compressão, 16 mil amostras por segundo, mono. O AudioWorklet é um pedaço de JS que roda na thread de áudio e recebe 128 amostras por chamada (8 ms). Ele converte cada uma para int16 e junta 512 num buffer: 1024 bytes, 32 ms. O buffer sai por `postMessage` sem cópia e vai direto para `ws.send` como mensagem binária.
- **Por quê:** o `MediaRecorder` só entrega áudio comprimido (Opus em WebM), em pedaços que ele escolhe. O servidor teria que decodificar, e isso soma latência. O `ScriptProcessorNode` faria o mesmo que o worklet, mas é obsoleto e roda na thread do React. O `AudioContext` nasce a 16 kHz, então o browser reamostra e o worklet só converte float → int16. Entrada é 16 kHz porque a fala inteligível cabe em 8 kHz de banda e é o que o Live pede. Saída é 24 kHz para a voz soar natural.
- **Onde:** `web/src/lib/ligacao/captura.worklet.js:17` (`process`), `:23` (float → int16), `:26` (`postMessage` com transferência); `web/src/lib/ligacao/captura.ts:17` (`AudioContext` a 16 kHz), `:27` (chunk vai ao `aoChunk`); `web/src/lib/ligacao/config.ts:6` (512 amostras).
- **Pergunta de entrevista:** "Por que você não usou o MediaRecorder?"
  **Resposta:** Ele entrega Opus comprimido, e o Gemini Live pede PCM cru. O AudioWorklet me dá as amostras cruas em tempo real, fora da thread do React. O contexto roda a 16 kHz, o worklet converte para int16 e junta em chunks de 32 ms, 1024 bytes.

### 3. Ticket de Ligação: o que o POST faz
- **Conceito:** o WebSocket do browser não manda header `Authorization`. Então o browser pede um Ticket por HTTP normal, com o Bearer: `POST /api/voz/ticket`. O servidor confere a Conversa, as vagas e o Cap, gera um código aleatório de 32 bytes e guarda em um dicionário em memória com validade de 30 s. O browser conecta em `wss://.../api/voz/ws?ticket=<código>`. Na conexão, o servidor faz `pop` do código: ele some no primeiro uso.
- **Por quê:** a URL fica no log do nginx. Um JWT ali valeria 24 h para quem lesse o log. O Ticket no log já está gasto. O `pop` acontece antes de checar a validade, então nem um Ticket expirado tem segunda tentativa. O POST recusa cedo o que o WebSocket recusaria (402, 404, 409, 429), porque erro HTTP o browser lê com clareza e close code depois do upgrade é mais pobre. Caiu: JWT na URL. Ressalva: o dicionário `TICKETS` vive em um processo só.
- **Onde:** `api/app/voz.py:239` (`criar_ticket`), `:253` (`secrets.token_urlsafe(32)`), `:262` (`_consumir`, com o `REVISAR(human)` em `:258`), `:216` (`_vaga`).
- **Pergunta de entrevista:** "Como você autentica um WebSocket se o browser não manda Authorization?"
  **Resposta:** Com um ticket de uso único, pedido por uma rota HTTP autenticada. Ele vale 30 s e só cobre o intervalo até o upgrade. Se vazar no log depois de usado, não dá acesso a nada. JWT na URL ficaria 24 h no log do nginx.

### 4. O upgrade de HTTP para WebSocket e o nginx
- **Conceito:** WebSocket começa como um `GET` HTTP com `Upgrade: websocket`. O servidor responde `101 Switching Protocols` e a mesma conexão TCP vira um canal aberto nos dois sentidos, sem novo pedido.
- **Por quê:** `Upgrade` e `Connection` são headers hop-by-hop: o nginx não os repassa. O nginx ainda fala HTTP/1.0 com o backend por padrão, e o nosso `Connection ""` global zerava o header. O backend nunca via o upgrade (400 ou 502). A location `/api/voz/ws` põe `Upgrade $http_upgrade`, `Connection "upgrade"` e `proxy_read_timeout 600s` (acima dos 540 s da Ligação). Repete os outros `proxy_set_header`, porque declarar um na location descarta os herdados. Caiu: mudar o `Connection ""` global, que afetaria o SSE. Prova sem gastar Gemini: ticket inválido dá close 4401 do app; se o nginx barrasse, viria 400 ou 502.
- **Onde:** `deploy/nginx-tess-chat.conf:45` (location); `api/app/voz.py:272` (`accept`) e `:275` (close 4401).
- **Pergunta de entrevista:** "Por que o WebSocket não passava pelo nginx, e como você provou que passou?"
  **Resposta:** O upgrade é um handshake HTTP com headers hop-by-hop, e o nginx não os repassa sozinho. Declarei `Upgrade` e `Connection upgrade` numa location só da Ligação. Para provar sem gastar Gemini, mandei um ticket inválido: o app fecha com 4401. Ver 4401 e não 502 prova que o upgrade atravessou.

### 5. O que o servidor faz ao abrir o WebSocket, em ordem
- **Conceito:** a rota `ligacao()` faz seis coisas, nesta ordem. (1) `accept`. (2) `_consumir` o ticket, senão close 4401. (3) `_vaga` de novo, senão close 4409 ou 4429. (4) `turnos.reservar(cid)`: ocupa a vaga da Conversa. (5) `_reservar` o crédito outra vez e monta a instrução com o histórico; sem espaço, close 4402. (6) `conectar(instrucao)` abre a sessão no Gemini; falha vira 4500. Só então grava `voice_call_started` e manda `pronto`.
- **Por quê:** o `accept` vem antes das recusas porque close antes do `accept` vira 403 HTTP, e o browser não lê close code. A checagem da vaga (3) e o registro em `LIGACOES` (logo antes de (4)) não têm `await` no meio, então dois WebSockets do mesmo Usuário não passam juntos. O Cap é conferido no POST e de novo aqui. INFERIDO o motivo: entre um e outro podem passar até 30 s, e o Ledger pode ter mudado. Nenhum ADR nem comentário diz isso. Qualquer falha antes do `pronto` chama `_liberar` para não deixar 409 eterno.
- **Onde:** `api/app/voz.py:269` (`ligacao`), `:276` (checagem sem `await`), `:279` (`turnos.reservar`), `:284` (`_reservar`), `:286` (`conectar`), `:297` (`voice_call_started`), `:306` (`pronto`).
- **Pergunta de entrevista:** "Se dois WebSockets abrem juntos com o mesmo ticket, o que acontece?"
  **Resposta:** O primeiro faz `pop` e leva o ticket. O segundo recebe `None` e fecha com 4401. Se forem dois tickets do mesmo Usuário, a checagem da vaga e o registro em `LIGACOES` acontecem sem `await` entre eles. O asyncio não troca de task ali, então só um passa e o outro leva 4409.

### 6. Proxy no servidor, não token efêmero no browser
- **Conceito:** o browser abre um WebSocket com o FastAPI, e o FastAPI abre outro com o Gemini Live. Cada byte passa pelo servidor nos dois sentidos. O browser nunca vê a chave do Gemini.
- **Por quê:** com token efêmero o browser falaria direto com o Google, e o servidor não veria o `usage_metadata`. O Cap e a auditoria dependeriam do que o browser reporta, e o browser pode mentir. Cap (ADR 0004) e auditoria (ADR 0007) são obrigatórios. Preço do proxy: um salto a mais, dezenas de ms (INFERIDO) contra centenas de ms do modelo. Caiu o token efêmero (menos código). Também caíram SSE (só vai em um sentido), WebRTC (exige servidor de mídia; o Gemini fala WebSocket) e a cascata STT → LLM → TTS (três peças, latência pior, e o reconhecimento do browser não funciona no Brave).
- **Onde:** `api/app/voz.py:67` (`_conectar`, abre a sessão), `:85` (`conectar_gemini`, o seam de teste), `:317` (`_relay`).
- **Pergunta de entrevista:** "Por que não deixar o browser falar direto com o Gemini?"
  **Resposta:** Porque o custo e a auditoria são obrigatórios e o servidor precisa ver o uso real. No proxy eu leio o `usage_metadata` de cada turno e gravo o acerto no Ledger. Direto, eu confiaria no número que o browser manda. O preço é um salto a mais, dezenas de ms contra centenas do modelo.

### 7. A Ligação ocupa a vaga de turno da Conversa
- **Conceito:** a Ligação chama `turnos.reservar(cid)`, o mesmo registro do turno de texto (`ATIVOS`, ADR 0023). Enquanto ela dura, `POST /api/chat/{cid}` recebe 409. A vaga sai no fim único, antes de o servidor mandar o `fim`.
- **Por quê:** duas respostas ao mesmo tempo na mesma Conversa brigam pelo histórico e pelo Crédito. Reusar a vaga dá o 409 de graça, sem lock novo. Regras de concorrência: uma Ligação por Usuário (`LIGACOES` é um dicionário por `user_id`) e teto global de 3 (`len(LIGACOES)`). Isso vale para um processo só.
- **Onde:** `api/app/voz.py:216` (`_vaga`), `:279` (`turnos.reservar`), `:566` (`_liberar`); `api/app/turnos.py:63` (`reservar`), `:71` (`encerrar`).
- **Pergunta de entrevista:** "O que acontece se o usuário manda texto durante a ligação?"
  **Resposta:** Recebe 409, o mesmo de um turno em andamento. A Ligação é um turno longo. A vaga sai antes do `fim`, então quando o browser recebe o `fim` já pode mandar texto.

### 8. O relay: duas tasks que encerram juntas
- **Conceito:** uma task lê do browser e manda para o Gemini (`_browser_para_gemini`). Outra lê do Gemini e manda para o browser (`_gemini_para_browser`). `asyncio.wait(FIRST_COMPLETED, timeout=540)` acorda quando uma acaba ou quando o tempo estoura. As duas são canceladas e esperadas (`gather`).
- **Por quê:** cada lado fala quando quer. O microfone não espera resposta, e o Gemini fala sem o browser pedir. Um laço só travaria esperando um dos dois. Esperar o cancelamento evita task órfã escrevendo num WebSocket fechado. O motivo do fim sai de quem acabou: `desligou` ou `queda` (devolvidos pela task), exceção vira `erro` (o Gemini caiu), timeout vira `limite`. O SDK termina o `receive()` a cada `turn_complete`, então a task do Gemini repete o laço; uma rodada sem nenhuma mensagem é o Gemini fechado, e vira `ConnectionError`.
- **Onde:** `api/app/voz.py:317` (`_relay`, `REVISAR(human)` em `:312`), `:321` (`asyncio.wait`), `:337` (`_browser_para_gemini`), `:387` (`_gemini_para_browser`), `:402` (rodada vazia).
- **Pergunta de entrevista:** "Se o usuário fecha a aba, como o servidor para de falar com o Gemini?"
  **Resposta:** A task do browser recebe `websocket.disconnect` e devolve `queda`. O `wait` acorda e cancela a task do Gemini. O `finally` roda o fim único: acerto, auditoria, vaga liberada. A sessão do Gemini fecha quando o `async with` sai.

### 9. O que cada mensagem carrega: browser → servidor → Gemini
- **Conceito:** o browser manda dois tipos de mensagem. **Binária** é sempre áudio (PCM 16 kHz): o servidor embrulha em `types.Blob(mime "audio/pcm;rate=16000")` e chama `send_realtime_input(audio=...)`. **Texto** é JSON com o campo `tipo`: `frame` (JPEG em base64, vira `Blob("image/jpeg")` e `send_realtime_input(video=...)`), `tela` (só grava auditoria) e `desligar` (encerra a task e devolve `desligou`).
- **Por quê:** binário para áudio evita base64 (33% a mais) em 31 chunks por segundo. Frame vai em base64 dentro do JSON porque é 1 por segundo e o canal de texto já existe. O servidor descarta Frame que chega antes de 0,8 × 1/fps: o cliente é dono do ritmo, mas o servidor não confia nele para o custo. JSON inválido é ignorado, não derruba a Ligação.
- **Onde:** `api/app/voz.py:337` (`_browser_para_gemini`), `:343` (áudio), `:356` (Frame), `:359` (`_frame`: limite de fps e decodificação), `:372` (`_tela`: evento só na mudança de estado, não por Frame).
- **Pergunta de entrevista:** "Se eu abrir o WebSocket e mandar 100 Frames por segundo, o que acontece?"
  **Resposta:** O servidor descarta o Frame que chega antes de 0,8 × 1 s do anterior. O que passa é no máximo ~1,25 por segundo. O custo de imagem não depende do browser se comportar.

### 10. O que volta do Gemini e como o servidor traduz
- **Conceito:** o Gemini manda `LiveServerMessage`, uma por vez, cada uma com um campo preenchido. `_traduzir` converte para o protocolo do browser e guarda o que precisa na Ligação. `inline_data` (bytes PCM 24 kHz) vira mensagem binária. `input_transcription` (uma vez, no fim da fala do usuário) vira `transcricao` de origem `usuario`. `output_transcription` (pedaços) vira `transcricao` do `agente` com o **texto acumulado** e `final:false`. `interrupted` vira `interrompido`. `turn_complete` fecha a fala do agente com `final:true` e chega junto do `usage_metadata` daquele turno.
- **Por quê:** acumulado (e não pedaço) porque o browser só troca o texto da fala aberta, sem juntar nada. Concatenar duplicaria o texto, porque o `final` repete a fala inteira. O `usage_metadata` é **por turno**, não por sessão, e cada turno traz o contexto inteiro de novo. Então o servidor soma todos. 40% das mensagens chegam vazias no SDK 2.25 (tipo novo do servidor, INFERIDO); o código ignora.
- **Onde:** `api/app/voz.py:406` (`_traduzir`), `:410` (uso), `:416` (transcrição do usuário), `:421` (áudio), `:424` (transcrição do agente), `:427` (`interrompido`), `:429` (`turn_complete`); `web/src/lib/ligacao/useLigacao.ts:40` (`juntarFala`) e `:108` (`onmessage`).
- **Pergunta de entrevista:** "O que o modelo manda de volta durante uma resposta?"
  **Resposta:** Chunks de áudio PCM 24 kHz, pedaços de transcrição e, no fim do turno, `turn_complete` com o uso daquele turno por modalidade. O servidor repassa o áudio como binário, monta a transcrição acumulada e guarda o uso para o acerto.

### 11. A tela: 1 fps, Frame de 264 tokens
- **Conceito:** `getDisplayMedia` devolve um vídeo da aba, janela ou tela que o usuário escolhe. A cada 1 s o código desenha o quadro atual num canvas (lado maior 1280, sem ampliar), codifica em JPEG 0,7 e manda em base64. O modelo não assiste vídeo: cada Frame é uma imagem que ele lê. A trilha tem o evento `ended` para o botão "Parar de compartilhar" da barra do browser.
- **Por quê:** o caso de uso é documento, código, slide e página, que mudam pouco por segundo. A Live API aceita no máximo 1 imagem por segundo. Movimento rápido (vídeo, jogo) fica fora. O pior caso é o agente ver a tela de até 1 s atrás. **O spike mediu 264 tokens por Frame a 1280 e a 768**: a resolução não muda o custo, só o tamanho do WebSocket. A regra do ADR 0028 (baixar para 768 acima de ~1000 tokens) não disparou. Doze Frames iguais contaram como 264, não 12 × 264 (INFERIDO: o servidor guarda só o mais recente ou descarta repetido). Por isso o acerto usa o `IMAGE` que o Gemini reporta, não uma conta por Frame. Custo por Frame: 264 × US$ 1/1M = US$ 0,00026. `ocupado` no laço pula o tique se o JPEG anterior não saiu.
- **Onde:** `web/src/lib/ligacao/tela.ts:18` (`compartilharTela`), `:26` (`setInterval` a 1000/fps), `:45` (`ended`), `:53` (`capturar`: canvas → JPEG → base64); `web/src/lib/ligacao/config.ts:11` (constantes); `api/app/voz.py:49` (`TOKENS_FRAME`).
- **Pergunta de entrevista:** "Por que não mandar a tela como vídeo?"
  **Resposta:** O modelo lê imagens, não assiste vídeo, e a API aceita no máximo 1 por segundo. Para documento e código, um quadro por segundo pega o que muda. Medi antes de decidir: 264 tokens por Frame a 1280 e a 768, então fiquei em 1280 e o custo é o mesmo.

### 12. O adendo de voz que fez o modelo negar a tela
- **Conceito:** o modelo de voz recebe uma instrução (system instruction). A primeira versão, do ADR 0026, dizia "sem tela, diga que não vê nada". Na sessão 1 do spike, com o Frame já no contexto (`IMAGE` = 264), o modelo respondeu que não tinha acesso à tela. A instrução nova diz primeiro que as imagens da tela chegam, e só depois o que fazer se não chegou nenhuma. Com ela, o modelo leu a tela nas sessões 2 e 3.
- **Por quê:** a frase solta sobre "sem tela" puxou a recusa. A sessão 2 mudou duas coisas juntas (instrução e 1 fps), então a causa não está isolada (INFERIDO). Ficou a instrução que funcionou. O prompt da Ligação é só o adendo, sem o `INSTRUCOES` do chat, que só fala de tools que a Ligação não tem. No smoke real de produção o problema voltou por outro motivo: com dispositivo falso ligado, o Brave entregou um padrão verde no lugar da aba, e o modelo disse com razão que não via nada. Foi defeito do teste, não do produto.
- **Onde:** `api/app/voz.py:39` (`ADENDO_VOZ`), `:180` (`_instrucao`); `spike/live/RESULTADO.md`, seção Sessões.
- **Pergunta de entrevista:** "Já viu o modelo dizer que não via a tela? O que era?"
  **Resposta:** Vi no spike. Com a instrução "sem tela, diga que não vê nada", ele negou a tela mesmo com o Frame no contexto. Troquei para dizer primeiro que as imagens chegam, e ele leu certo. Mudei a instrução e o fps ao mesmo tempo, então não sei qual dos dois pesou. Está registrado como INFERIDO.

### 13. Barge-in: o usuário fala por cima
- **Conceito:** barge-in é o usuário falar enquanto o agente fala, e o agente parar. Quem detecta a voz é o VAD do Gemini (detecção de atividade de voz, automática). Ele manda `voice_activity`, depois `server_content.interrupted`. O servidor repassa `{"tipo":"interrompido"}`. O browser esvazia a fila de áudio.
- **Por quê:** o Gemini manda o áudio em rajada, mais rápido que o tempo real. Quando o usuário interrompe, o browser já tem segundos de fala agendados. Sem esvaziar, o agente seguiria falando por cima. O `echoCancellation` do microfone evita que a voz do próprio agente dispare o barge-in. VAD no cliente caiu: seria mais código e duas fontes de verdade. A fala cortada do agente segue aberta no browser: o servidor fecha no `turn_complete` que vem em seguida.
- **Onde:** `api/app/voz.py:427` (`interrompido`); `web/src/lib/ligacao/useLigacao.ts:123` (`interrompido` → `esvaziar`); `web/src/lib/ligacao/reproducao.ts:43` (`esvaziar`); `web/src/lib/ligacao/captura.ts:14` (`echoCancellation`).
- **Pergunta de entrevista:** "Como o agente para de falar quando o usuário interrompe?"
  **Resposta:** O Gemini detecta a voz e manda `interrupted`. O backend repassa como `interrompido`. No browser, a fila guarda cada chunk agendado e para todos na hora. O cancelamento de eco do microfone evita que o agente se interrompa sozinho.

### 14. A fila de reprodução: PCM 24 kHz no alto-falante
- **Conceito:** cada chunk binário que chega vira um `Int16Array`, depois floats (divide por 32768), depois um `AudioBuffer` de 24 kHz, depois um `AudioBufferSourceNode`. O nó é agendado para começar quando o anterior termina (`proximo`). Chunks que chegam em rajada tocam colados, sem buraco nem sobreposição. `esvaziar` chama `stop()` em todas as fontes e zera o `proximo`.
- **Por quê:** tocar assim que chega sobreporia os chunks. Agendar pelo relógio de áudio (`currentTime`) dá reprodução contínua mesmo com a rede irregular. O tamanho da fila (`fontes.size`) diz se o agente está falando.
- **Onde:** `web/src/lib/ligacao/reproducao.ts:21` (`tocar`), `:32` (`proximo`), `:33` (`start`), `:43` (`esvaziar`).
- **Pergunta de entrevista:** "O áudio chega em pedaços. Como você evita picotar?"
  **Resposta:** Cada pedaço vira um nó agendado para o instante em que o anterior termina, pelo relógio do `AudioContext`. Se a fila está vazia, começa agora. Se não, emenda no fim. Assim tocam colados, e para interromper eu paro todos os nós.

### 15. O histórico entra na Ligação, e as falas voltam para a Conversa
- **Conceito:** ao abrir, `historico_em_texto` lê as últimas Mensagens de usuário e assistente (só o texto) e monta "Usuário: ... / Assistente: ...". Esse texto vai no fim da instrução do Gemini. O teto é 4000 tokens, contados a 3 caracteres por token (INFERIDO), do mais novo para o mais antigo; a Mensagem que estoura sai inteira. No fim, `gravar_falas` grava as falas como Mensagens: **um par usuário/assistente por troca**, com a parte `{"type":"data-ligacao"}`. Falas seguidas do usuário viram uma Mensagem só. Texto vazio não entra. O front mostra "por voz" quando acha a parte.
- **Por quê:** o chat, a Compactação e o corte de histórico contam turnos por Mensagem de usuário. Um bloco com a Ligação inteira seria um turno gigante, sem onde cortar. Com pares, o resto do sistema não sabe a diferença. Imagem e PDF não vão ao Live: custam caro e a voz não precisa. `data-ligacao` segue o padrão `data-turno-interrompido`: sem migração, o modelo de texto ignora `data-*`, e o link compartilhado leva a marca. Caiu: mandar o histórico como turnos com `send_client_content` (outro caminho no seam).
- **Onde:** `api/app/voz.py:164` (`historico_em_texto`), `:180` (`_instrucao`), `:473` (`_trocas`), `:491` (`_mensagem`), `:496` (`gravar_falas`); `web/src/pages/Chat.tsx:526` (`porVoz`).
- **Pergunta de entrevista:** "Como a Ligação sabe o que foi dito antes no chat? E o que fica no chat depois?"
  **Resposta:** No início eu monto um texto com as últimas Mensagens, só texto, e mando na instrução do Gemini, cortando do mais antigo para caber em 4000 tokens. No fim gravo um par usuário/assistente por troca, com uma parte `data-ligacao`. Tudo que já existe conta turno por Mensagem, então a Compactação funciona sem mudar.

### 16. Sem Jev e sem tools na Ligação
- **Conceito:** a Ligação não tem Roteador e não tem tools. O agente só conversa e olha a tela.
- **Por quê:** o Jev força a tool no passo 1 de um turno de requisição e resposta. A Ligação é fluxo contínuo de áudio, sem "passo 1". Um roteador na frente atrasaria a fala. Caiu: reusar o Roteador por turno de voz.
- **Onde:** `api/app/voz.py:67` (`_conectar`: a config não tem `tools`); `docs/adr/0026-ligacao-por-gemini-live-com-proxy-websocket.md`, item 6.
- **Pergunta de entrevista:** "Por que a Ligação não usa tools nem o Roteador?"
  **Resposta:** O Roteador força a tool antes da chamada, num turno de requisição e resposta. A voz é um fluxo contínuo, e um roteador na frente atrasa a fala. Sem tools, a Ligação só conversa e olha a tela. É um limite assumido.

### 17. Crédito, parte 1: a reserva (onde é conferida)
- **Conceito:** no POST do ticket e de novo ao abrir o WebSocket, `_reservar` calcula o **custo máximo** de 9 min e chama `caber`. `caber` soma o Ledger do Usuário e o global (`_gasto`), soma a reserva e compara com o Cap. Passou do Cap: grava o evento `cap_reached` e levanta `CapAtingido`, que vira **402** no POST ou close **4402** no WebSocket. O custo máximo vem de `uso_maximo`: 25 tokens/s de áudio in e out por 540 s, mais 264 tokens por Frame a 1 Frame/s. Ao preço de tabela dá **US$ 0,345**.
- **Por quê:** o ADR 0027 dizia ~US$ 0,25. O número subiu porque o spike mediu Frame a 264 tokens contados cada um (o ADR contava imagem mais barata). **A reserva não segura nada**: não grava linha, não bloqueia saldo. Ela só confere que "gasto de agora + 0,345" cabe no Cap. O ADR 0027 diz que "a reserva segura ~US$ 0,25 durante a Ligação". O código não faz isso; a divergência está em `docs/LACUNAS.md`. Duas chamadas simultâneas podem passar juntas (ressalva no comentário de `api/app/credito.py:131`). E 0,345 não é teto real: cada turno cobra o contexto de novo (INFERIDO). Preço de tabela mesmo na chave free: senão o custo real seria zero e o Cap nunca dispararia.
- **Onde:** `api/app/voz.py:148` (`uso_maximo`), `:154` (`_reservar`), `:249` (no ticket), `:284` (no WebSocket); `api/app/credito.py:129` (comentário "não grava a reserva"), `:142` (`caber`), `:148` (compara), `:160` (`CapAtingido`); `api/app/main.py:62` (402).
- **Pergunta de entrevista:** "Como o Cap protege uma ligação de 9 minutos?"
  **Resposta:** No início eu calculo o custo máximo de 9 minutos, US$ 0,345 ao preço de tabela, e só deixo abrir se o gasto atual mais isso cabe no Cap do Usuário e no global. Sem espaço, 402. Ressalva que eu falo sozinho: a reserva é uma checagem, não um bloqueio de saldo. Nada é gravado até o fim, e duas chamadas simultâneas podem passar juntas.

### 18. Crédito, parte 2: o acerto (onde é gravado)
- **Conceito:** no fim, `_acertar` soma o `usage_metadata` de todos os turnos (`lig.uso`), cada modalidade no seu preço: texto in US$ 0,75, áudio in US$ 3, imagem in US$ 1, texto out US$ 4,50, áudio out US$ 12, pensamento US$ 4,50 (por 1M de tokens). Arredonda para cima em micro-USD. Grava **uma linha** no Ledger (`credit_ledger`), com `message_id` nulo. Sem nenhum `usage_metadata` (caiu antes do 1º `turn_complete`), estima: 25 tokens/s de entrada durante a duração, 25 tokens/s de saída sobre os bytes de áudio recebidos ÷ 48000, e 264 tokens se chegou Frame. A linha leva `estimado: true` no `voice_call_ended`.
- **Por quê:** cada turno cobra o contexto inteiro de novo, então a soma é o custo. Pegar só o último cobraria menos. O `thoughts_token_count` fica fora do `total_token_count`, então entra à parte, como saída de texto (INFERIDO, o ADR 0027 não tinha linha para pensamento). O turno cortado no fim (desligou no meio da resposta) não entra. Tabela de Preço: três colunas novas (`audio_input`, `image_input`, `audio_output`), nulas nos modelos de texto (migração 0024). Caiu: uma linha de preço por modalidade com nome de modelo inventado.
- **Onde:** `api/app/voz.py:101` (`UsoLigacao.somar`), `:135` (`debit_ligacao`), `:441` (`_acertar`, `REVISAR(human)` em `:436`), `:452` (`session.add(CreditLedger(...))`), `:532` (chamada em `_encerrar`); `api/migrations/versions/0024_preco_gemini_live.py`.
- **Pergunta de entrevista:** "Como você cobra uma ligação que a chave free não cobra?"
  **Resposta:** Pelo preço de tabela do modelo pago, cada modalidade no seu preço: áudio, imagem, texto e pensamento. Somo o uso de todos os turnos que o Gemini reporta. O Crédito mede quanto custaria, então o Cap continua funcionando. Se a Ligação cai sem nenhum reporte, estimo por duração e marco `estimado`.

### 19. O fim único
- **Conceito:** desligar, limite de 9 min, queda do browser e queda do Gemini passam por `_encerrar`, chamado do `finally` da rota. A ordem é fixa: (1) `gravar_falas` com commit; (2) acerto e `voice_call_ended` com commit; (3) `_liberar` a vaga (mesmo se o acerto falhar); (4) manda `fim` e fecha com 1000. A flag `encerrada` segura uma segunda chamada. Motivo `queda` não manda `fim`, porque o browser já saiu.
- **Por quê:** quatro caminhos de fim com código próprio esqueceriam um passo, e a Conversa ficaria em 409 eterno. Cada passo tem `try` próprio: falha na gravação das falas não impede o acerto, e falha no acerto não impede a vaga sair. A vaga sai antes do `fim` para o browser poder mandar texto ao recebê-lo. Gemini que não abre (4500) não passa aqui: não começou, então sem `voice_call_started`, uso nem Ledger.
- **Onde:** `api/app/voz.py:516` (`_encerrar`, `REVISAR(human)` em `:512`), `:308` (`finally`), `:557` (`_liberar` no `finally` interno), `:566` (`_liberar`).
- **Pergunta de entrevista:** "O que garante que a vaga da Conversa sempre é liberada?"
  **Resposta:** Todo fim passa por uma função só, chamada do `finally`. Dentro dela, cada passo tem o seu `try`, e a liberação da vaga fica num `finally` interno. Mesmo se a gravação das falas ou o acerto falharem, a vaga sai. Sem isso, um erro deixaria 409 eterno na Conversa.

### 20. A origem `ligacao` no Ledger
- **Conceito:** o Ledger não tem coluna de origem. A origem é derivada da linha. Com `message_id` é `resposta`. Sem `message_id` e modelo do Jev, `roteador`. Sem `message_id` e modelo Live, `ligacao`. O resto é `compactacao`. O front mostra "Ligação"; origem desconhecida mostra o nome cru.
- **Por quê:** coluna nova exigiria migração e mexeria no Ledger somente-inserção. O modelo Live só existe na Ligação. Custo dessa escolha: se trocarem `GEMINI_LIVE_MODELO` na config, Ligações antigas passam a aparecer como Compactação. Antes do ticket 82, a Ligação aparecia como `compactacao` no custo da Conversa.
- **Onde:** `api/app/credito.py:323` (`_origem`); `web/src/components/CustoConversa.tsx` (rótulo).
- **Pergunta de entrevista:** "Como o painel sabe que aquele custo é de uma Ligação?"
  **Resposta:** Pela linha do Ledger: sem `message_id` e com o modelo Live. Não criei coluna nova. O ganho é zero migração. O custo é que trocar o modelo Live na config reclassifica as Ligações antigas.

### 21. Latência: o que foi medido
- **Conceito:** a latência que o usuário sente é do fim da fala até o primeiro som do agente. Ela inclui a pausa que o VAD espera para ter certeza de que a pessoa parou, a geração do modelo e a rede. O script de smoke embrulha o `WebSocket` no browser e guarda o instante do último chunk de microfone com sinal e o do primeiro chunk de áudio recebido.
- **Por quê:** medir no servidor esconderia a rede. Medir no browser mostra o que o usuário sente. Resultado: 0,5 a 0,6 s com servidor local; 1,9 s em produção (rede residencial → VPS), 3,3 s na sessão em que o modelo não viu tela. A causa da diferença entre local e produção não foi isolada: pode ser a rede, o salto extra pelo VPS, ou a variação do modelo (INFERIDO). O `thinking_level` baixo aparece no guia do Gemini como alavanca de latência. Não foi testado.
- **Onde:** `web/scripts/smoke-ligacao-prod.mjs` (`window.__ws`); `spike/live/RESULTADO.md`, linha de latência.
- **Pergunta de entrevista:** "Quanto demora o agente para começar a falar?"
  **Resposta:** Local, 0,5 a 0,6 s. Em produção, 1,9 s na sessão em que ele leu a tela, medido no browser, da minha rede residencial até o VPS. Não isolei se é rede, o salto do proxy ou o modelo. O próximo experimento é `thinking_level` baixo e medir de uma rede melhor.

### 22. Como testei sem gastar crédito
- **Conceito:** três níveis. (1) `pytest` com um Gemini falso injetado pelo seam `conectar_gemini` (`dependency_overrides`): 15 testes. (2) O front real no Brave contra um servidor WebSocket falso que segue o protocolo, com microfone falso. (3) E2E com a API real e um Gemini roteirizado, e o smoke de produção com um WAV de pergunta tocado como microfone e um canvas com o pedido de compra no lugar da tela.
- **Por quê:** o que importa é o que o chamador vê. Nos testes: `pytest` afirma o Ledger, a auditoria, o 409, a vaga liberada e o que o Gemini falso recebeu e devolveu (ele é a fronteira do sistema, não a unidade testada). No front: chunks de 1024 bytes, Frames a cada ~1000 ms, fila vazia depois do `interrompido`. O smoke de produção mostrou que com `--use-fake-device-for-media-stream` o `getDisplayMedia` do Brave devolve um padrão verde. Trocamos por `canvas.captureStream()`. Trilha, 1 fps, JPEG 1280 e WebSocket seguem reais.
- **Onde:** `api/tests/test_voz.py:245` (relay), `:298` (Ledger no desligar), `:324` (queda do browser); `web/scripts/testar-ligacao.mjs`; `web/scripts/e2e-ligacao.mjs`; `web/scripts/smoke-ligacao-prod.mjs`.
- **Pergunta de entrevista:** "Como você testou voz e tela sem ninguém falando?"
  **Resposta:** Em três níveis. De graça: Gemini falso no `pytest` e servidor falso no front. Depois E2E com a API real e um Gemini roteirizado. Por último, produção com um WAV de pergunta como microfone e um canvas como tela. O primeiro smoke mostrou que a captura de aba não funciona com dispositivo falso, e eu troquei por canvas.

### 23. Limites assumidos e próximos passos
- **Conceito:** o que a Ligação não faz hoje, dito de frente.
- **Por quê:** cada limite tem custo de código maior que o ganho na demo (YAGNI).
  - **9 min.** Sem *session resumption*. O Gemini derruba a conexão em ~10 min. Próximo passo: reconectar com o `handle` que o servidor já manda (`session_resumption_update`).
  - **Um processo só.** `TICKETS`, `LIGACOES` e `ATIVOS` são dicionários em memória. Restart ou deploy no meio derruba a Ligação. Mais de um processo pede mover a sessão para um worker ou Redis.
  - **Reserva não segura saldo.** Próximo passo: gravar uma linha de reserva no Ledger e ajustar no acerto.
  - **Sem tools e sem Jev.** Ver parada 16.
  - **Free tier treina com o conteúdo.** Voz e tela vão para o Google. Aceito para demo; não compartilhe dado sensível.
  - **Sem `thinking_level`.** Latência pode cair; não foi testado.
  - **Frame repetido não é detectado.** Custa centavos; não compensa.
- **Onde:** ADR 0026 (Consequências), ADR 0028 (Consequências), `docs/DECISOES-AUTONOMAS.md` (linhas do ticket 76).
- **Pergunta de entrevista:** "O que você faria com mais uma semana?"
  **Resposta:** Primeiro, session resumption, para Ligações acima de 9 minutos. Segundo, reserva gravada no Ledger, para o Cap valer de verdade durante a chamada. Terceiro, testar `thinking_level` baixo e medir a latência de novo. Depois, mover a sessão para fora do processo para poder escalar.
