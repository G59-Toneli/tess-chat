# 31 — Erro de tool MCP volta ao modelo; não vira "provedor falhou"

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 30
**Refs:** `api/app/chat.py` (`ERROS_PROVEDOR`, `_erro`, 502), `api/app/resiliencia.py`, `api/app/mcp.py`, `api/app/tools.py` (teto de texto por chamada, evento `tool_call`), ADR 0012, ADR 0009. Caso real do Toneli em 23/09 15:14 UTC, usuário demo, conversa "pagamento para o Gustavo" (tools `stripe_cf8f_*`).

**O que aconteceu (auditoria):** planner → account_info → api_search → api_details (result 36.267 chars) → api_write `PostPaymentLinks` com `line_items[0]` cheio de chaves inventadas (`price_data_raw`, `price_dataAuto`, `price_data_unit`...). O Stripe respondeu "Tool execution was interrupted by an error". O app devolveu ao usuário "O provedor do modelo falhou. Tente de novo." (502) e não gravou `tool_call` da escrita.

**Investigar primeiro (registrar no ticket, seção "Do spike"):**
1. Que exceção o `MCPToolset` levanta quando a tool devolve `isError=true`, e por que ela caiu em `ERROS_PROVEDOR` (ou em `FallbackExceptionGroup`). Reproduzir com o servidor demo devolvendo erro.
2. O resultado de 36 k chars do `api_details` chegou inteiro ao Gemini ou foi cortado pelo teto de texto? O teto vale para MCP? Se cortou, o modelo perdeu o schema e inventou.
3. Se o schema `parameters: object` sem propriedades do Stripe é o que faz o Gemini inventar chaves (comparar com um turno em que o details volta inteiro).

**What to build:**
- Erro de tool (nativa ou MCP) NÃO é erro de provedor. Voltar ao modelo como resultado de tool com o texto do erro (Pydantic AI: `ModelRetry` ou retorno de erro), permitindo 1 nova tentativa dentro do teto de tool calls. Se a tool falhar de novo, encerrar o turno com aviso legível "A tool X falhou: <motivo>" (mesmo caminho do ticket 30 para turno interrompido). Gravar `tool_call` com `erro` no payload em toda falha.
- Teto de texto por chamada: manter, mas quando cortar, anexar ao resultado a frase "[resultado cortado em N caracteres; peça só o trecho necessário]" para o modelo saber. Para `*_details`/schemas, avaliar teto maior (ex. 40 k chars) e registrar em DECISOES.
- Prompt de sistema: uma linha sobre tools MCP genéricas ("para tools `*_api_write`, use exatamente os nomes de parâmetros devolvidos por `*_api_details`; não invente campos").
- Front: o erro de tool aparece no card da tool com o texto do servidor, e a mensagem final do assistente explica.

**Aceite:**
- [ ] Teste: servidor MCP demo com tool que devolve `isError` → o modelo recebe o erro, tenta de novo, e o turno termina com resposta (FunctionModel). Evento `tool_call` com `erro`.
- [ ] Teste: tool falha 2 vezes → turno encerra com aviso legível, sem 502, Mensagem persistida.
- [ ] Teste: resultado acima do teto vem com a frase de corte.
- [ ] Turno real com Stripe (máx. 2, sandbox): "cria um link de pagamento de R$ 1000 para o produto Tess Assistant" fecha com link `buy.stripe.com/test_...`. Se ainda falhar, registrar exatamente os args que o modelo mandou.
- [ ] `uv run pytest tests/test_chat.py tests/test_mcp.py tests/test_resiliencia.py tests/test_tools.py` verde; `tsc` e `npm run build` limpos.
