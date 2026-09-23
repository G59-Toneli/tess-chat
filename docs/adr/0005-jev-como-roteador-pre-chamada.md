# ADR 0005 — Jev (TypeSafe) como Roteador pré-chamada com gate de confiança

**Status:** aceito, 2026-09-23

## Contexto
Jev responde perguntas tipadas (sim/não, escolha, nota) com probabilidade. Só texto, inglês primário, 70 a 500 ms, US$ 0,042 por 1M. Toneli já testou em português sem perda percebida.

## Decisão
Antes de chamar o Gemini, o Roteador pergunta ao Jev: precisa de Tool? Qual, entre as ativas na Conversa? Se a confiança fica no limiar ou acima, força a tool via `function_calling_config` (`ANY` mais `allowedFunctionNames`). Abaixo do limiar, deixa o Gemini decidir (`AUTO`). Tudo vira Evento de auditoria com a distribuição devolvida.

## Consequências
- Chamada ao Gemini fica mais previsível quando a confiança é alta.
- Jev nunca gera texto nem vê Anexos. Recebe só o texto do turno e a lista de Tools.
- Smoke test em português com ~10 casos reais é pré-requisito (ticket 11).
- Fraco contra injeção no `state`: o Roteador só decide tool, nunca permissão.
