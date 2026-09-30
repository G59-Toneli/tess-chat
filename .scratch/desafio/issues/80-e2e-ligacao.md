# 80 — Ligação ponta a ponta: E2E com mídia falsa e smoke real em produção

**Type:** task (web/ + api/)
**Status:** resolved
**Blocked by:** 76, 78, 79
**Refs:** ADR 0026 a 0028, `docs/PROTOCOLO-LIGACAO.md`.

**Objetivo:** provar que a Ligação funciona inteira, primeiro de graça, depois de verdade.

## Escopo
1. **E2E sem custo:** Playwright com Chromium e `--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` (microfone e tela falsos), contra a API local com o Gemini falso do 76. Fluxo: abrir Conversa, ligar, compartilhar tela, receber áudio e transcrição, desligar, ver as falas no histórico (se o 77 estiver resolvido), ver `voice_call_ended` em `/auditoria`.
2. **Smoke real em produção:** 2 a 3 Ligações de até 2 min no Brave, em `chat.toneli.dev.br`, com uma aba com texto compartilhada. Perguntar sobre o texto. Medir a latência do fim da fala ao primeiro áudio (declarar host e rede). Conferir o Ledger e a auditoria.
3. Defeito achado: corrigir se for pequeno, senão abrir ticket de ajuste.

## Aceite
- E2E verde, script commitado.
- Smoke: resultado, latência medida e chamadas no LEDGER. Screenshot em `.scratch/desafio/screens/80-*`.
- Chamadas reais: teto 3 sessões de até 2 min (dentro do teto de 10 da etapa).

## Paradas de estudo
1 a 2 entradas no formato do `docs/ESTUDO-VOZ.md`: como testar áudio e tela sem microfone de verdade.

### A. Áudio e tela sem microfone: dispositivo falso, arquivo WAV e canvas
- **Conceito:** o Brave tem flags para fingir microfone (`--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream` sem diálogo). Com `--use-file-for-fake-audio-capture=<wav>%noloop` o "microfone" toca um WAV uma vez. A tela vira uma trilha de `canvas.captureStream()` no lugar do `getDisplayMedia`.
- **Por quê:** sem gente falando, o smoke real precisa de fala de verdade (WAV pt-BR gerado pelo TTS do Windows, com 8 s de silêncio na frente para dar tempo de compartilhar a tela). Caiu: `--auto-select-tab-capture-source-by-title`. Com o dispositivo falso ligado, o `getDisplayMedia` do Brave devolve um padrão verde falso e ignora a aba (o 1º smoke provou: "não consigo ver nada"). O canvas mantém o resto do caminho real: trilha, 1 fps, JPEG 1280, WebSocket.
- **Onde:** `web/scripts/smoke-ligacao-prod.mjs` (flags e canvas), `web/scripts/e2e-ligacao.mjs`, `api/scripts/servidor_e2e.py` (Gemini roteirizado).
- **Pergunta de revisão:** "Como você testou voz e tela sem ninguém falando?"
  **Resposta:** Dois níveis. De graça, a API real com um Gemini de mentira que responde a cada 30 chunks de áudio, e o browser com microfone e tela falsos. De verdade, um WAV com a pergunta tocado como microfone e um canvas com o pedido de compra como tela, em produção, 2 sessões. O 1º smoke mostrou que a captura de aba não funciona com dispositivo falso, então troquei por canvas.

### B. Medir latência no browser
- **Conceito:** a latência que o usuário sente é do fim da fala até o 1º som do agente. O script embrulha o `WebSocket` no browser: guarda o instante do último chunk de microfone com sinal e do 1º chunk de áudio recebido.
- **Por quê:** medir no servidor esconderia a rede. Medir no browser inclui rede residencial até o VPS mais o VAD e a geração do Gemini.
- **Onde:** `web/scripts/smoke-ligacao-prod.mjs` (`window.__ws`).
- **Pergunta de revisão:** "Quanto demora o agente para começar a falar?"
  **Resposta:** 1,9 s na sessão em que ele leu a tela, 3,3 s na que ele pensou antes de responder, medido no browser (Windows do Toneli, rede residencial, VPS `<ip-do-vps>`). O tempo inclui a pausa que o Gemini espera para ter certeza de que a pessoa parou. O spike local deu 0,4 a 0,9 s.

## Answer
E2E sem custo verde (10 checagens): API real na 8018 com Gemini roteirizado, Brave com mídia falsa, Ligação com tela, transcrição, áudio, desligar, falas no histórico, `voice_call_ended` na API e em `/auditoria`. Smoke em produção, 2 sessões Live: a 1ª falhou por defeito do harness (padrão verde no lugar da tela, o modelo disse que não via nada); a 2ª leu "4827-B" e "1.350 reais e 90 centavos". Latência 1,9 s (2ª) e 3,3 s (1ª), fim da fala até o 1º áudio, medida no browser. Ledger: `origem: ligacao`, 6012 e 4098 micro-USD. Ressalva: a 2ª sessão desligou antes do `turn_complete`, então o custo foi estimado (`estimado: true`, `turnos: 0`), caminho previsto no acerto. Nada `REVISAR(human)`.
