# 30 — Teto de tool calls: visível no chat, configurável, e card da tool sem sobreposição

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ticket 06b (teto), ticket 14 (Configuração), `docs/LACUNAS.md` (turno cortado não é cobrado), `api/app/chat.py`, `api/app/configuracao.py`, `web/src/components/BlocoTool.tsx`. Caso real do Toneli em 23/09 11:40 com o MCP do Stripe.

**Problema:** com o Stripe MCP, uma escrita gasta 3 chamadas (`stripe_api_search` → `stripe_api_details` → `stripe_api_write`). O teto fixo de 5 por turno cortou o turno na 6ª chamada (`tool_limit_reached` na auditoria). O front ficou com o último card em "Rodando" e sem mensagem: parece travado. Além disso, no card da tool a latência ("218 ms") é desenhada em cima do badge "Concluída".

**What to build:**
1. **Fim visível.** Quando o turno termina por `tool_limit_reached`, o stream emite um evento próprio; o front marca o card em andamento como "Interrompida" e mostra um aviso na mensagem do assistente: "Turno interrompido: limite de N chamadas de tool. Você pode aumentar o limite em Configuração." com link. A Mensagem do assistente é persistida com esse aviso, para aparecer ao recarregar. Mesmo tratamento para timeout de tool MCP (15 s) e servidor MCP fora do ar no meio do turno.
2. **Teto configurável.** Campo `tool_calls_limite` na Configuração (herança conversa → usuário → `.env`, como os outros). Default do `.env` sobe de 5 para 10. UI em `/config`, seção Limiares, com a explicação "Quantas chamadas de tool um turno pode fazer. MCPs genéricos gastam 3 por ação." Migração `0018`.
3. **Cobrança do turno cortado.** O turno que bate no teto já gastou tokens em N requests: acertar a reserva com o uso real (fecha a lacuna do `docs/LACUNAS.md`). Registrar em DECISOES-AUTONOMAS e atualizar LACUNAS.
4. **Card da tool.** Latência e badge de estado em elementos separados, sem sobreposição, em qualquer largura. Nome longo de tool MCP (`stripe_5f8e_stripe_api_search`) trunca com reticências e mostra inteiro no title; o prefixo do servidor pode virar um badge pequeno com o nome do servidor ("Stripe").

**Aceite:**
- [ ] Teste: turno com FunctionModel que pede 6 tools e teto 5 → evento `tool_limit_reached`, Mensagem do assistente persistida com o aviso, ledger acertado com o uso real.
- [ ] Teste: `tool_calls_limite` por conversa sobrepõe o do usuário.
- [ ] Screenshot dark `30-turno-interrompido.png` (card "Interrompida" + aviso) e `30-card-tool.png` (badge e latência lado a lado com nome longo).
- [ ] `tsc`, `npm run build`, `uv run pytest tests/test_chat.py tests/test_configuracao.py tests/test_resiliencia.py tests/test_mcp.py` verdes.
