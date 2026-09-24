# 58 — Medir o custo fixo por chamada e estabilizar o cache entre turnos

**Type:** task (api/)
**Status:** resolved
**Refs:** pedido do Toneli em 23/09, depois do e2e do ticket 55. Roda em paralelo com a outra sessão (ticket 57, migração 0022). Este ticket NÃO cria migração.

**Baseline (prod, conta demo, gemini-3.8-flash, conv `132fa3e6-cba3-4877-bb4d-bf139020f489`). Não remedir:**
- msg 222 (turno Notion, ~17 chamadas, 16 tool calls): input 1.251.511, cache_read 1.104.378.
- msg 232 (turno seguinte, 1 chamada, sem tool): input 82.791, cache_read 0.
- Soma das `parts` com resultados de tool no turno: ~47k chars (~15k tokens). O resto (~65k tokens por chamada, INFERIDO) é system prompt + schemas de 61–64 tools.
- Rodapé mostrou "64 tools" no turno 1 e "61 tools" no turno 2.

**Problema:** o custo fixo por chamada come a janela. O gatilho da Compactação (`compactacao_limiar` 100k) lê o `input_tokens` da última resposta, então os schemas empurram a rosca e a Compactação. Entre turnos o cache implícito do Gemini zerou.

**Aceite:**
1. **Medição por chamada, aditiva.** Evento de auditoria novo `llm_request` (um por ModelResponse do run), com input, cache_read, output, número de tools enviadas e um hash do prefixo (instructions + tool defs em ordem). Sai de `result.all_messages()` / `ModelResponse.usage`. Nenhum comportamento muda. Sem migração (usar colunas/JSON que `audit_events` já tem).
2. **Script `api/scripts/medir_prefixo.py`**: para um usuário, monta instructions + tool defs exatamente como o turno monta e chama `count_tokens` do Gemini (sem geração). Imprime tokens do system prompt, das tools por servidor MCP e total. Vai rodar em produção pelo orquestrador (`docker compose exec app`), então não pode depender de nada do dev.
3. **Diagnóstico do cache zero entre turnos**, com evidência no código: a lista de tools muda entre turnos (roteador/Jev escolhendo categoria? servidor MCP fora?), a ordem de `list_tools` é determinística, há algo dinâmico antes das tools no prompt? Consultar a doc do cache implícito do Gemini (mínimo, TTL). Se a correção for estabilizar ordem/prefixo sem mudar o conjunto de tools, aplicar. Se exigir mudar o conjunto de tools ou o gatilho da Compactação, NÃO aplicar: descrever em `docs/LACUNAS.md` com opções.
4. **Golden de regressão (modelo fake, CI):** replay do turno Notion usando um MCP fake com schemas de tamanho parecido. Afirma: as mesmas tools ficam disponíveis ao modelo, a ordem é estável entre dois turnos, o hash do prefixo é igual entre dois turnos seguidos com o mesmo conjunto. Não asserta contagem de tokens reais.
5. Suíte do chat verde, `tsc` limpo se tocar em web/. `REVISAR(human)` no ponto que extrai o uso por chamada. Atualizar `DECISOES-AUTONOMAS.md`.

**Tetos:** Gemini `count_tokens` até 5 chamadas; geração 0 (as medições reais ficam com o orquestrador, autorizadas pelo Toneli). Jev 0. Tavily 0.

## Answer
- Evento `llm_request` por ModelResponse (`api/app/medicao.py`, chamado no `_persistir`): input, cache_read, output, nº de tools e `prefix_hash`. Aditivo, sem custo, sem migração.
- Causa do cache zero, com evidência no código: a ordem das tools não era determinística (`select(McpServer)` sem `ORDER BY` em `tools.py:324`; `UPDATE` do refresh OAuth em `mcp_oauth.renovar` pode mover a linha no heap, INFERIDO; `list_tools` sem ordem garantida). Corrigido: `Medidor.prepare_tools` ordena por nome. O conjunto de tools mudou entre os turnos (64 → 61), e isso sozinho já zera o cache; causa exata e opções em `docs/LACUNAS.md`, com o TTL não documentado e o gatilho da Compactação.
- `api/scripts/medir_prefixo.py`: `--seco` sem chamada; sem ele, 3 + 1 countTokens por grupo. Local, com o MCP falso de 12 tools: 9.523 tokens de prefixo.
- `REVISAR(human)`: `auditar_requests` (pareamento request ↔ ModelResponse por índice).
