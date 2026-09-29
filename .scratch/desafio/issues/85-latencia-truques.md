# 85 — Latência da Ligação, rodada 2: truques para cortar o tempo real e o percebido

**Type:** bug/pesquisa (api/ + web/)
**Status:** resolved
**Blocked by:** —
**Refs:** ticket 83 e `docs/LATENCIA-LIGACAO.md` (leia inteiro), ADR 0026 e 0028, `spike/live/RESULTADO.md`. Pedido do Toneli em 29/09: "deve ter alguma gambiarra inteligente".

**Estado:** a rede pesa menos de 50 ms. O tempo está no Gemini: detecção de fim de fala (VAD) ~0,8 a 0,9 s depois do 83, e o modelo começa a falar entre 0,4 e 3 s depois (pensamento). Total em produção: 2,3 a 3,9 s.

## Escopo
1. **Pesquisa (fonte primária + relatos de quem faz voice agent em produção: docs do Gemini Live, LiveKit, Pipecat, Vapi, Retell, blogs de engenharia).** Liste truques, cada um com ganho esperado (ms, real ou percebido), custo de implementação e risco. Candidatos a checar, sem se limitar a eles:
   - `thinking_budget` (0 ou baixo) no `gemini-3.8-live`, ou um modelo Live sem pensamento (`gemini-3.1-flash-live-preview`, `gemini-2.5-flash-native-audio-*`), medindo qualidade de leitura da tela junto.
   - **Contexto crescendo por Frame:** 264 tokens por Frame a 1 fps = ~16k tokens por minuto no contexto. Isso deve aumentar o tempo até o primeiro token ao longo da Ligação. Testes: mandar Frame só quando a tela muda (diff barato no canvas), ou só quando o usuário começa a falar; cortar o histórico injetado.
   - VAD no cliente (ex.: Silero via `@ricky0123/vad-web`) com detecção manual (`activity_start`/`activity_end`) em vez do VAD automático do servidor.
   - `audio_stream_end` ou equivalente ao detectar silêncio.
   - Latência percebida: som curto local ("hmm", clique) ou indicador visual assim que o fim da fala é detectado, enquanto o modelo pensa. Vale dizer no vídeo que é mascaramento.
   - Silêncio de volta para ~800 ms, se os 500 ms partem frase.
2. **Experimento: um truque por vez**, na ordem de ganho esperado por custo, com a trilha `?trace=1` do 83. Mesma harness, mesmo host, n ≥ 3 por variante. Medir também se a leitura da tela piora.
3. **Aplicar o que funcionar.** Mudança mínima. Se contrariar um ADR (ex.: diff de Frame contra o item 4 do ADR 0028), escrever ADR novo (0029) com o porquê.
4. **Documentar para o Toneli:** em `docs/LATENCIA-LIGACAO.md`, seção "Rodada 2": cada truque pesquisado (o que é, por que funciona, fonte), o que foi testado, a tabela, o que ficou e o que caiu. Atualizar `docs/ESTUDO-VOZ.md` (paradas novas) e a pergunta da latência em `docs/ROTEIRO-VIDEOS.md`.

## Aceite
- `test_voz.py` e `web/scripts/e2e-ligacao.mjs` verdes.
- Tabela por variante em produção, n ≥ 3, host declarado.
- Chamadas reais: teto 8 sessões Live de até 2 min, chave free (R$ 0). Nenhuma chamada paga.

## Paradas de estudo
3 entradas no formato do `docs/ESTUDO-VOZ.md`, uma por truque que ficou.

## Answer
Pesquisei 5 truques (pensamento mínimo, menos contexto por Frame, VAD no cliente, latência percebida, silêncio/`prefix_padding`) e testei 4 em produção, 6 sessões Live de 65 s + 12 conexões curtas, chave free, R$ 0. Mediana no browser: padrão 1785 ms (n=6), `m31` 1406 ms (n=5), `pens0` 2448 ms (n=3), `fq` 4073 ms (n=3, ruído de VAD). Ficou: indicador "pensando" (aos 0,42 s, mascaramento) e `?v=m31` como opt-in. Caíram `thinking_budget=0` (pensamento zera, tempo não cai) e cortar Frame (mesmo tempo, -45% de Frame). VAD no cliente fica como próximo passo (mexe no ADR 0026). Sem ADR novo: nada mudou o padrão. Ressalva: n pequeno e o Gemini varia mais de 1 s entre horas. Detalhe em `docs/LATENCIA-LIGACAO.md`, "Rodada 2". Nada `REVISAR(human)`; 3 paradas em `docs/ESTUDO-VOZ.md` (26 a 28), a 28 não é truque de latência.
