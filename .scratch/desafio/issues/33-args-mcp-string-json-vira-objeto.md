# 33 — Args de tool MCP: string JSON vira objeto antes de enviar

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 31
**Refs:** ticket 31 (seção "Do spike": args exatos que o Gemini mandou), `api/app/tools.py` (`ComTeto.call_tool`), `api/app/mcp.py`, ADR 0009.

**Problema:** com schema aberto (`parameters: object` sem propriedades, caso do Stripe), o Gemini envia objetos aninhados como string JSON: `"price_data": "{\"currency\":\"brl\",...}"`. O Stripe recusa ("Invalid object"). A 2ª tentativa repete o erro, e o turno fecha sem o link.

**What to build:**
1. Em `ComTeto.call_tool` (ou no ponto único por onde passam os args de tool MCP), antes de enviar: percorrer os args recursivamente; valor string que começa com `{` ou `[` e faz `json.loads` com sucesso vira objeto/lista. Só para tools de origem `mcp`. Registrar em DECISOES-AUTONOMAS (por quê: limitação do Gemini com schema aberto; o servidor recebe o tipo certo; risco: string legítima que parece JSON, aceito).
2. Erro de validação de args (Pydantic) na 2ª tentativa hoje vira chunk de erro antes do `ComTeto`: fazer passar pelo mesmo caminho do "A tool X falhou".
3. Card da tool: na 1ª falha, não mostrar o texto escrito para o modelo ("Fix the errors and try again."); mostrar só o motivo do servidor.

**Aceite:**
- [ ] Teste: args com string JSON aninhada chegam ao servidor MCP demo como objeto (tool demo que ecoa os tipos).
- [ ] Teste: string comum ("Olá {mundo}") não é alterada.
- [ ] Turno real com Stripe (máx. 2, sandbox): "cria um link de pagamento de R$ 1000 para o produto Tess Assistant" fecha com link `buy.stripe.com/test_...`. Screenshot dark `33-stripe-link.png`.
- [ ] `uv run pytest tests/test_mcp.py tests/test_tools.py tests/test_chat.py` verde; `tsc` e `npm run build` limpos.
