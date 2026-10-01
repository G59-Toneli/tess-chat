# 11 — Roteador Jev pré-chamada com gate de confiança

**Type:** task (AFK + HITL)
**Status:** resolved
**Blocked by:** 10
**Refs:** ADR 0005. Spike hipótese 9. Skill `typesafe:typesafe-ai`.

**What to build:** módulo `router` que monta uma pergunta Choice com as tools ativas + `nenhuma`, chama o Jev com o texto do turno, e devolve `{tool, confidence, distribution}`. Se confiança ≥ limiar (Configuração, default 0.7), o Agent roda com `function_calling_config` forçando a tool. Senão, `AUTO`. Evento `router_decision` com a distribuição. Débito no ledger com preço do Jev.

Testes primeiro.

**Aceite:**
- [ ] Os 10 casos do spike passam como teste de regressão (golden set).
- [ ] Jev indisponível (429/529) → fallback `AUTO` e evento `router_fallback`, chat não quebra.

**Do spike:** os 10 casos e as descrições das opções estão em `spike/`. Caso 10 (ambíguo, "resume esse PDF" sem anexo) espera confidence abaixo do limiar, não uma tool. O state leva o campo de anexos presentes.

## Answer
Módulo `api/app/roteador.py` (nome do glossário: Roteador). Choice com as Tools ativas + `nenhuma`, descrições do spike no módulo, state com texto e anexos. `Gate` força a Tool só no passo 1 (Gemini recebe `ANY`); depois volta a AUTO. Evento `router_decision` com distribuição e custo; débito `jev-latest` no Ledger. Falha do Jev (429/529, rede, sem chave) vira AUTO com `router_fallback`.
Golden set: 10 casos gravados uma vez em `tests/fixtures/jev_golden.json` (9/9; caso 10 com confiança 0.47). `ler_pdf` não existe no registro: entra no golden set como Tool de teste.
Ressalvas: limiar em `settings.roteador_limiar` até o ticket 14. Smoke real no Gemini mostrou o modelo chamando `web_search` 4 vezes após o passo forçado (fora do escopo; teto de tool calls é do 06b).
`nenhuma` vira AUTO).
