# 36 — Roteador não força tool de origem MCP

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 35
**Refs:** ADR 0005 (Roteador), `api/app/roteador.py`, `api/app/chat.py` (montagem da escolha), tickets 33 e 35 ("Do spike": Jev forçou `stripe_implementation_planner` com 0,78 e 0,83 para pedidos de criar pagamento).

**Problema:** o Jev vê nomes e descrições de tools de terceiros que não foram desenhadas para roteamento (`implementation_planner`, `search_documentation`, `send_feedback`, `api_search`...). Ele escolhe o planner para "gera o pagamento" e o `tool_choice` força o modelo a chamar uma tool que só explica. O turno termina sem ação. Com tools nossas (web_search, gmail_send) o Roteador acerta porque o conjunto é pequeno e conhecido.

**Decisão (emenda ao ADR 0005, escrever seção "Emenda 23/09" no próprio ADR):** o Roteador só **força** tool de origem `nativa` ou `google`. Para tool de origem `mcp`, ele grava `router_decision` com `forcada=false` e o modelo escolhe livre (`tool_choice=auto`). Motivo: o Jev não tem contexto para escolher entre tools genéricas de um servidor externo, e forçar errado custa o turno inteiro. Alternativa descartada: excluir tools MCP da entrada do Jev (perde o registro da decisão para a Auditoria e a Tela do Roteador).

**What to build:** a mudança acima em `roteador.py`/`chat.py`, teste, emenda no ADR, linha em `docs/MOTIVACOES.md`. A linha "roteado para X" no chat mostra "sugerido" em vez de "escolheu" quando não forçou.

**Aceite:**
- [ ] Teste: decisão do Jev em tool `mcp` com confiança 0,9 → `forcada=false` e `tool_choice` ausente; em tool `nativa` com 0,9 → forçada como hoje.
- [ ] Turno real com Stripe (máx. 2, sandbox), frase: "quero cobrar um amigo meu, ele comprou de mim um celular, no valor de 1000 reais, gera o pagamento pra mim" → link `buy.stripe.com/test_...`. Screenshot dark `36-stripe-celular.png`. Se ainda falhar, registrar os args de cada `api_write`.
- [ ] `uv run pytest tests/test_roteador.py tests/test_chat.py tests/test_mcp.py` verde; `tsc` e `npm run build` limpos.
