# ADR 0028 — Captura de tela a 1 fps, JPEG, resolução configurável

**Status:** aceito, 2026-09-28. Resolução inicial INFERIDA até o spike (ticket 75) medir tokens por frame.

## Contexto
A Live API aceita imagem JPEG a no máximo 1 fps. O modelo não assiste a tela como vídeo: cada frame vira uma imagem de centenas de tokens que o modelo lê. O caso de uso é documento, código, slide e página web, que mudam pouco por segundo. A 384 px o texto fica ilegível. O Gemini 3.x divide imagem grande em pedaços, e cada pedaço custa tokens.

## Decisão
Toneli, 28/09:
1. **`getDisplayMedia`** no browser. O usuário escolhe aba, janela ou tela. Sem suporte (celular), o botão de compartilhar some e a Ligação fica só voz.
2. **1 fps, JPEG, qualidade 0,7, lado maior de 1280 px.** Fps e resolução são config, não constante.
3. **Regra de ajuste:** o spike mediu mais de ~1000 tokens por frame a 1280 px, testar 768 px antes de baixar o fps.
4. **Sem detectar frame repetido.** Imagem custa ~US$ 0,002/min; otimizar não compensa (YAGNI).
5. Fim do compartilhamento pela barra do browser (`track.onended`) atualiza a UI e para os frames.

### Alternativas descartadas
- **Mais que 1 fps.** A API não aceita.
- **384 px.** Barato, mas o modelo não lê texto.
- **Diff de frame.** Economiza centavos com código a mais.

## Consequências
- Movimento rápido (jogo, vídeo) fica fora: o agente vê um quadro por segundo.
- A pergunta sobre "o que está na tela agora" vê um frame de até 1 s atrás.
