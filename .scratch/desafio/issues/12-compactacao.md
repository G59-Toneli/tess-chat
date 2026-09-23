# 12 — Compactação automática do histórico

**Type:** task (AFK + HITL)
**Status:** blocked
**Blocked by:** 08
**Refs:** ADR 0006.

**What to build:** `ProcessHistory` que, quando os tokens de entrada do turno anterior passam do limiar da Configuração, resume as mensagens antigas com flash-lite mantendo os últimos N turnos literais, sem separar tool-call de resultado. Resumo persistido em `summaries` (conversa, até_mensagem_id, texto, tokens). Próximas chamadas usam resumo + mensagens após o corte. Evento `compaction` com tokens antes/depois. Débito do resumo no ledger. Front: marcador "histórico compactado aqui".

**HITL:** a função `should_compact(usage, settings) -> bool` fica com `TODO(human)`. Testes primeiro.

**Aceite:**
- [ ] Com limiar 2.000 tokens, a 4ª mensagem de uma conversa longa dispara compactação sem erro e a resposta continua coerente com o começo da conversa.
- [ ] Mensagens originais continuam na UI e no banco.
- [ ] Teste: nenhum resumo corta entre tool-call e resultado.
