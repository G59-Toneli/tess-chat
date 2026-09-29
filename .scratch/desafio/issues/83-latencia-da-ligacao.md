# 83 — Latência da Ligação em produção: achar a causa e corrigir

**Type:** bug (api/ + web/ + deploy/ se preciso)
**Status:** resolved
**Blocked by:** —
**Refs:** ADR 0026, `docs/PROTOCOLO-LIGACAO.md`, Answer do 75 (0,4 a 0,9 s local, script direto no Gemini), do 76 (0,5 a 0,6 s, API local 8015) e do 80 (1,9 s e 3,3 s em produção, browser em rede residencial → VPS <ip-do-vps>). Pedido do Toneli em 29/09.

**Problema:** do fim da fala ao primeiro áudio do agente, produção leva 1,9 a 3,3 s; local leva ~0,5 s. A causa não foi isolada.

## Escopo
1. **Medir por salto antes de mexer.** Timestamps (monotônicos no servidor, `performance.now()` no browser) em: último chunk de fala enviado pelo browser; chegada no servidor; envio ao Gemini; primeira resposta do Gemini no servidor (e o tipo: transcrição, áudio); chegada do primeiro áudio no browser; início da reprodução. Log só em dev ou atrás de flag; nada de dado sensível.
2. **Hipóteses a testar, uma por vez:**
   - O fim da fala não é sinalizado: o áudio falso acaba e nada mais chega, então a detecção de voz do Gemini espera o silêncio. Conferir se o browser continua mandando silêncio (microfone real manda) e se `audio_stream_end` ou os parâmetros de detecção de voz (`silence_duration_ms`, `end_of_speech_sensitivity` ou equivalentes reais do SDK em `spike/live/RESULTADO.md`) mudam o tempo.
   - Buffer no caminho: `proxy_buffering` na location do WebSocket, Nagle/TCP_NODELAY, chunks grandes demais no relay ou na fila de reprodução do browser (o browser espera acumular antes de tocar?).
   - Frames competindo com o áudio no mesmo socket (medir com e sem tela).
   - Distância VPS → Google (medir RTT do VPS para o endpoint do Gemini e comparar com o da máquina local).
   - Trabalho síncrono no loop asyncio do relay (reamostragem, base64, JSON grande).
   - Pensamento do modelo base (o spike viu `thoughts_token_count`): conferir se dá para reduzir o orçamento de pensamento na config do Live.
3. **Corrigir a causa medida.** Mudança mínima. Se forem várias, corrigir as que pesam mais que ~200 ms.
4. **Documentar:** `docs/LATENCIA-LIGACAO.md` com a tabela por salto antes e depois (host, rede, porta declarados), a causa, o fix e o que foi descartado. Atualizar os números em `docs/ESTUDO-VOZ.md` e `docs/ROTEIRO-VIDEOS.md` (pergunta difícil da latência). ADR novo só se o fix mudar uma decisão do 0026.

## Aceite
- Tabela antes/depois em produção, mesma medição, mesmo host cliente.
- Testes do `test_voz.py` e o E2E do 80 (`web/scripts/e2e-ligacao.mjs`) verdes.
- Chamadas reais: teto 3 sessões Live de até 2 min (a etapa está em 7 de 10; chave free, R$ 0). Precisar de mais: pare e reporte.

## Paradas de estudo
2 entradas no formato do `docs/ESTUDO-VOZ.md`: onde o tempo ia e por que o fix resolve.

## Answer
A rede não é a causa: cliente→VPS 12 ms, VPS→Google 2 ms, ida e volta pelo relay 40 a 50 ms; a mesma harness local deu 1,7 s (produção 1,9 s), e os 0,5 s dos tickets 75 e 76 vinham de outra régua. O tempo está no Gemini: o VAD levava 1,3 s para fechar a fala e o modelo pensava de 0,4 a 3 s. Fix: `end_of_speech_sensitivity=HIGH` e `silence_duration_ms=500` no `_conectar`, e trilha por salto atrás de `?trace=1`. O VAD caiu de 1292 para 823 a 926 ms (~400 ms), mas o total em produção não caiu (3,9, 3,3 e 2,3 s, n=3; antes 1,9 e 3,3 s): o pensamento do modelo variou mais e o `gemini-3.8-live` não aceita `thinking_level`. Ressalvas: dois parâmetros mudados juntos, uma pergunta de três foi partida pelo VAD, e "antes" local tem n=1. Frames competindo não foi testado. Tabela e descartes em `docs/LATENCIA-LIGACAO.md`. Nada `REVISAR(human)`.

