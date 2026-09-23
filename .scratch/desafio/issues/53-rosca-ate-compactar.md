# 53 — Rosca de contexto mede até a Compactação, não até a janela do modelo

**Type:** task (web/)
**Status:** resolved
**Refs:** ticket 32 (indicador de contexto), ticket 49. Pedido do Toneli em 23/09.

**Problema:** a rosca usava como base a janela do modelo (~1 mi no Gemini). Como a Compactação dispara bem antes (padrão 100 mil), a rosca ficava sempre quase vazia e não avisava nada útil.

**Decisão (Toneli, 23/09):** a base passa a ser o limiar de Compactação efetivo (Conversa → conta → padrão), que `/contexto` já devolvia. Rosca cheia = acima do limiar. As faixas de cor (70 % / 90 %) seguem iguais, agora contra o limiar. Sai o risco que marcava o limiar dentro da rosca. A janela do modelo fica só na tooltip, como informação.

## Answer
`web/src/lib/contexto.ts`: `fracao` divide pelo limiar. `resumo` mostra "X de Y tokens até compactar (pct) · faltam Z · janela do modelo W". Acima do limiar, mostra "acima do limiar de compactação: o histórico antigo vai ser resumido", sem prometer "no próximo turno" (com menos de 3 turnos a Compactação não roda). `IndicadorContexto.tsx`: sem a marca do limiar.
Validado no browser local, sem custo: estado normal (`screens/53-rosca-ate-compactar.png`) e acima do limiar, com o limiar da Conversa em 250 por um momento e revertido depois (`screens/53-rosca-acima-do-limiar.png`).
