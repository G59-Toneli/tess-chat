# 35 — Tool MCP com objeto livre: o modelo vê string JSON, o servidor recebe objeto

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 33
**Refs:** tickets 31 e 33 (seções "Do spike"), `api/app/tools.py` (`desembrulhar_json`, toolset auditado), `api/app/mcp.py` (como o `MCPToolset` entrega as tool definitions), ADR 0009. Caso real do Toneli em 23/09 12:57 (-03), servidor `stripe_16ef`.

**Problema:** `stripe_api_write.parameters` é `{"type":"object"}` sem propriedades. Com esse schema, o Gemini não emite objeto aninhado: manda `price_data: null` e inventa chaves (`line_items_array`, `price_data_data`, `price_dataparams`, `price_data_placeholder`). Duas tentativas, dois erros do Stripe, turno cortado. O desembrulho do 33 não ajuda porque o modelo nem chega a produzir a string.

**Investigar primeiro:** qual schema chega ao Gemini para `stripe_api_write` (dump da tool definition depois das transformações do Pydantic AI/GoogleModel). Confirmar se `additionalProperties` é removido e o objeto vira vazio. Registrar em "Do spike".

**What to build:**
1. **Reescrita de schema para tools MCP.** No toolset nosso (wrapper do `MCPToolset`), ao expor a definição ao modelo: todo parâmetro de tipo `object` sem `properties` (ou com `additionalProperties` livre) vira `{"type":"string","description":"<descrição original> — JSON serializado do objeto"}`. Ao receber a chamada, converter a string em objeto (reuso de `desembrulhar_json`) antes de repassar ao servidor MCP. Mesmo tratamento para `array` de objetos livres. Só para origem `mcp`. Registrar em DECISOES-AUTONOMAS: limitação conhecida do Gemini com schema aberto; o servidor recebe exatamente o que o schema original pede; o evento `tool_call` grava os args já convertidos.
2. **Orientação no prompt de sistema**, uma frase: "com tools `*_api_write`, prefira operações planas em cadeia (crie o recurso pai, use o id no filho) em vez de objetos aninhados".
3. Manter o retry do 31.

**Aceite:**
- [ ] Teste: definição exposta ao modelo para a tool do servidor demo com objeto livre tem o campo como `string`; a chamada com string JSON chega ao servidor como objeto (tool `tipos` do demo).
- [ ] Teste: parâmetro que já tem `properties` não é alterado.
- [ ] Turno real com Stripe (máx. 2, sandbox), com a frase exata do Toneli: "quero cobrar um amigo meu, ele comprou de mim um celular, no valor de 1000 reais, gera o pagamento pra mim" → link `buy.stripe.com/test_...` sem erro no card. Screenshot dark `35-stripe-celular.png`.
- [ ] `uv run pytest tests/test_mcp.py tests/test_tools.py tests/test_chat.py` verde; `tsc` e `npm run build` limpos.

## Do spike

Dump de `stripe_cf8f_stripe_api_write` passado por `GoogleModel.customize_request_parameters` e `_function_declaration_from_tool` (gemini-3.8-flash, banco de dev 5433):
- O schema chega ao Gemini igual ao registro: `parameters: {"type":"object","description":"Parameters for the API call..."}`, sem `properties` e sem `additionalProperties` (o Stripe nem declara). A hipótese "additionalProperties removido" está errada no mecanismo: quem remove é o `GoogleOpenAPISchemaTransformer`, só usado na Live API. O `GoogleModel` manda `parameters_json_schema` sem mexer.
- `tool_config` vai com `mode: VALIDATED` (perfil `google_supports_strict_tool_definition=True`). VALIDATED impõe o schema declarado no lado da API. Objeto sem propriedades declaradas só aceita objeto vazio: por isso `price_data: null` e chaves inventadas no nível de cima.

## Answer

`Auditada.get_tools` expõe ao modelo, só em tool MCP, o schema reescrito por `schema_para_modelo`: `object` sem `properties` (ou `array` desses) vira `string` com "JSON serializado"; objeto com `properties` só é percorrido. O `call_tool` já desembrulhava a string (33). Prompt de sistema ganhou a frase das operações planas em cadeia. 47/47 no pytest do aceite.
Turno real (sandbox, API nova 8005, Brave): a frase do Toneli foi roteada pelo Jev para `stripe_implementation_planner` (forçada, 0,78), igual ao 33. O modelo só explicou o passo a passo, sem `api_write`. Screenshot `35-stripe-celular-planner.png`. O follow-up na mesma Conversa passou do roteador, mas o script fechou o browser antes do fim do stream. Nenhum `api_write` rodou, então o aceite do link NÃO foi cumprido.
Ressalva: o roteamento para o planner é outro problema, fora deste ticket. O comentário acima de `INSTRUCOES` no chat.py ainda diz `parameters: object` (partição: só a frase).
