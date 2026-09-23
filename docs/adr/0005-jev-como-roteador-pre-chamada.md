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

## Emenda 23/09 — tool de origem MCP não é forçada
O Roteador só **força** tool de origem `nativa` ou `google`. Para tool de origem `mcp`, grava `router_decision` com `forcada=false` (e `sugerida=true` quando passou do limiar), e o modelo escolhe livre (`tool_choice=auto`). A linha do Roteador no chat mostra "sugeriu" em vez de "escolheu".

**Motivo:** o Jev não tem contexto para escolher entre tools genéricas de um servidor externo, que não foram desenhadas para roteamento (`implementation_planner`, `search_documentation`, `send_feedback`). Nos tickets 33 e 35 ele forçou o planner do Stripe para "gera o pagamento", e o turno terminou sem ação. Forçar errado custa o turno inteiro.

**Alternativa descartada:** excluir as tools MCP da entrada do Jev. Perde o registro da decisão para a Auditoria e a Tela do Roteador.

## Revisão (2026-09-23)
O Jev não vê o conteúdo dos Anexos, mas recebe o nome e o mime type de cada um. O `state` leva `anexos_na_mensagem`: lista de `filename` (ou `media_type`, sem nome), ou `"nenhum"` (`_rotear` em `api/app/chat.py`, `decidir` em `api/app/roteador.py`). Bytes nunca vão ao Jev.

**Por quê:** ticket 11. Sem esse campo, "resume esse PDF" parece igual com e sem PDF anexado. O caso 10 do golden set do spike ("resume esse PDF" sem anexo) espera confiança abaixo do limiar.
