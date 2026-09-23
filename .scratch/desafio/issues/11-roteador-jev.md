# 11 — Roteador Jev pré-chamada com gate de confiança

**Type:** task (AFK + HITL)
**Status:** blocked
**Blocked by:** 10
**Refs:** ADR 0005. Spike hipótese 9. Skill `typesafe:typesafe-ai`.

**What to build:** módulo `router` que monta uma pergunta Choice com as tools ativas + `nenhuma`, chama o Jev com o texto do turno, e devolve `{tool, confidence, distribution}`. Se confiança ≥ limiar (Configuração, default 0.7), o Agent roda com `function_calling_config` forçando a tool. Senão, `AUTO`. Evento `router_decision` com a distribuição. Débito no ledger com preço do Jev.

**HITL:** a função `apply_gate(decision, threshold) -> ToolChoice` fica com `TODO(human)`. Testes primeiro.

**Aceite:**
- [ ] Os 10 casos do spike passam como teste de regressão (golden set).
- [ ] Jev indisponível (429/529) → fallback `AUTO` e evento `router_fallback`, chat não quebra.

**Do spike:** os 10 casos e as descrições das opções estão em `spike/`. Caso 10 (ambíguo, "resume esse PDF" sem anexo) espera confidence abaixo do limiar, não uma tool. O state leva o campo de anexos presentes.
