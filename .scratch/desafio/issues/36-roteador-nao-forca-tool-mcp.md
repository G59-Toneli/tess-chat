# 36 — Roteador não força tool de origem MCP

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 35
**Refs:** ADR 0005 (Roteador), `api/app/roteador.py`, `api/app/chat.py` (montagem da escolha), tickets 33 e 35 ("Do spike": Jev forçou `stripe_implementation_planner` com 0,78 e 0,83 para pedidos de criar pagamento).

**Problema:** o Jev vê nomes e descrições de tools de terceiros que não foram desenhadas para roteamento (`implementation_planner`, `search_documentation`, `send_feedback`, `api_search`...). Ele escolhe o planner para "gera o pagamento" e o `tool_choice` força o modelo a chamar uma tool que só explica. O turno termina sem ação. Com tools nossas (web_search, gmail_send) o Roteador acerta porque o conjunto é pequeno e conhecido.

**Decisão (emenda ao ADR 0005, escrever seção "Emenda 23/09" no próprio ADR):** o Roteador só **força** tool de origem `nativa` ou `google`. Para tool de origem `mcp`, ele grava `router_decision` com `forcada=false` e o modelo escolhe livre (`tool_choice=auto`). Motivo: o Jev não tem contexto para escolher entre tools genéricas de um servidor externo, e forçar errado custa o turno inteiro. Alternativa descartada: excluir tools MCP da entrada do Jev (perde o registro da decisão para a Auditoria e a Tela do Roteador).

**What to build:** a mudança acima em `roteador.py`/`chat.py`, teste, emenda no ADR, linha em `docs/MOTIVACOES.md`. A linha "roteado para X" no chat mostra "sugerido" em vez de "escolheu" quando não forçou.

**Aceite:**
- [ ] Teste: decisão do Jev em tool `mcp` com confiança 0,9 → `forcada=false` e `tool_choice` ausente; em tool `nativa` com 0,9 → forçada como hoje.
- [ ] Turno real com Stripe (máx. 2, sandbox), frase: "quero cobrar um amigo meu, ele comprou de mim um celular, no valor de 1000 reais, gera o pagamento pra mim" → link `buy.stripe.com/test_...`. Screenshot dark `36-stripe-celular.png`. Se ainda falhar, registrar os args de cada `api_write`.
- [ ] `uv run pytest tests/test_roteador.py tests/test_chat.py tests/test_mcp.py` verde; `tsc` e `npm run build` limpos.

## Answer

`apply_gate` recebe a origem da Tool escolhida e devolve AUTO para `mcp`; o `router_decision` grava `forcada=false` e `sugerida=true` quando passou do limiar. A linha do chat mostra "Roteador sugeriu". Emenda 23/09 no ADR 0005 e linha no MOTIVACOES. 49/49 no pytest do aceite; tsc e build limpos.
Turno real (sandbox, API nova 8006, Brave, 1 turno): Jev deu `stripe_implementation_planner` 0,78, agora sem forçar. O próprio Gemini (flash-lite, modelo configurado na conta demo) escolheu o planner em AUTO e só explicou o passo a passo. Nenhum `api_write` rodou, então não há args a registrar. Aceite do link NÃO cumprido. Screenshot `36-stripe-celular.png`.
Ressalva: o problema saiu do Roteador e ficou no modelo. Não gastei o 2º turno para não passar do teto de Gemini.
