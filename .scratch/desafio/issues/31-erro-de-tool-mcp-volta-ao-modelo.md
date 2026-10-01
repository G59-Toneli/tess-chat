# 31 — Erro de tool MCP volta ao modelo; não vira "provedor falhou"

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 30
**Refs:** `api/app/chat.py` (`ERROS_PROVEDOR`, `_erro`, 502), `api/app/resiliencia.py`, `api/app/mcp.py`, `api/app/tools.py` (teto de texto por chamada, evento `tool_call`), ADR 0012, ADR 0009. Caso real do Toneli em 23/09 15:14 UTC, usuário demo, conversa "pagamento para o Fulano" (tools `stripe_cf8f_*`).

**O que aconteceu (auditoria):** planner → account_info → api_search → api_details (result 36.267 chars) → api_write `PostPaymentLinks` com `line_items[0]` cheio de chaves inventadas (`price_data_raw`, `price_dataAuto`, `price_data_unit`...). O Stripe respondeu "Tool execution was interrupted by an error". O app devolveu ao usuário "O provedor do modelo falhou. Tente de novo." (502) e não gravou `tool_call` da escrita.

**Investigar primeiro (registrar no ticket, seção "Do spike"):**
1. Que exceção o `MCPToolset` levanta quando a tool devolve `isError=true`, e por que ela caiu em `ERROS_PROVEDOR` (ou em `FallbackExceptionGroup`). Reproduzir com o servidor demo devolvendo erro.
2. O resultado de 36 k chars do `api_details` chegou inteiro ao Gemini ou foi cortado pelo teto de texto? O teto vale para MCP? Se cortou, o modelo perdeu o schema e inventou.
3. Se o schema `parameters: object` sem propriedades do Stripe é o que faz o Gemini inventar chaves (comparar com um turno em que o details volta inteiro).

## Do spike (23/09, exec-31)

Reproduzido com o demo: `hora_atual` com fuso inválido devolve `isError`. Mesmo sintoma do caso real.

1. **Hipótese 1: confirmada, é a causa raiz.** `MCPToolset` (padrão `tool_error_behavior='retry'`) converte `isError` em `ModelRetry`. `max_retries=None` herda `retries` do Agent, e o chat roda `Agent(retries=0)`. O ToolManager checa `retries >= 0` na primeira falha e levanta `UnexpectedModelBehavior("Tool ... exceeded max retries count of 0")`. Ela não está em `ERROS_PROVEDOR`: não grava `llm_error` nem `llm_call`, não persiste Mensagem. O adapter vira chunk `error` e o front mostra "O provedor do modelo falhou" para qualquer chunk de erro. **Não foi 502:** o stream já tinha 200. A auditoria real confirma (sem `llm_error`).
   - "Tool execution was interrupted by an error." não é do Stripe: é o texto que o adapter do Pydantic AI põe na tool pendente quando o run explode. O erro real do Stripe se perdeu.
   - O `tool_call` da escrita faltou porque `Auditada` só audita depois do retorno com sucesso.
2. **Hipótese 2: refutada.** `LIMITE_CHARS` só vale no `web_fetch`. Resultado MCP não tem teto: os 36.267 chars do `api_details` chegaram inteiros ao Gemini.
3. **Hipótese 3: fator contribuinte, INFERIDO.** O modelo inventou chaves com o schema completo no contexto. O schema do `api_write` é `parameters: object` sem propriedades, e o Agent do chat não tem prompt de sistema. Não dá para provar sem turno comparativo; o turno real do aceite mede o efeito da linha de prompt.

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

## Answer

Causa raiz: hipótese 1. `isError` vira `ModelRetry`, e com `Agent(retries=0)` o Pydantic AI levanta `UnexpectedModelBehavior`, que escapa de `ERROS_PROVEDOR` e vira chunk de erro. Não era 502. Agora o Agent roda com `retries=1`: o erro volta ao modelo, e a segunda falha seguida da mesma tool corta o turno no `ComTeto` com o aviso "A tool X falhou: <motivo>" (evento `mcp_tool_failed`). `Auditada` grava `tool_call` com `erro` em toda falha. Resultado MCP ganhou teto de 40k e todo corte leva a frase. Uma linha de prompt de sistema sobre `*_api_details`. Front sem código novo: o card já mostra `errorText`, e o aviso mostra o texto da API.
Turno real com Stripe (1 de 2, 5 requests Gemini): o mecanismo funcionou, mas **sem link**. O modelo mandou `price_data` como string JSON nas duas tentativas: `{"stripe_api_operation_id": "PostPaymentLinks", "parameters": {"line_items": [{"quantity": 1, "price_data": "{ \"currency\": \"brl\", \"unit_amount\": 100000, \"product_data\": { \"name\": \"Tess Assistant\" } }"}]}}`. O Stripe respondeu "Invalid object". Não gastei o 2º turno: sem mudança, a string se repetiria. Causa provável (INFERIDO): o Gemini serializa objeto aninhado como string quando o schema é `parameters: object` sem propriedades. Correção candidata para ticket novo: desembrulhar string JSON em args de tool MCP antes de enviar.

