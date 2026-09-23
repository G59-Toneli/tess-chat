# tess-chat

Chat com tools, vision, PDF, MCP, compactação, cap de crédito e auditoria. Desafio técnico com prazo 29/09/2026 12h.

## Leia antes de qualquer coisa
- `CONTEXT.md`: glossário. Use esses termos no código e na conversa.
- `docs/adr/`: toda decisão de arquitetura. Não contrarie um ADR sem escrever outro.
- `docs/WORKFLOW.md` e `docs/AGENT-PROMPT.md`: como o trabalho é executado por agentes.
- `docs/UI-GUIA.md`: obrigatório para qualquer mudança em `web/`.
- `.scratch/desafio/map.md`: destino, decisões, névoa. `issues/`: tickets. `LEDGER.md`: histórico de execução. `HANDOFF.md`: estado do orquestrador.
- `docs/DECISOES-AUTONOMAS.md`: decisões que agentes tomaram sozinhos. `REVISAR(human)` no código marca funções que o Toneli precisa estudar.

## Regras fixas
- Toneli precisa defender cada decisão em entrevista. Explique o porquê, não só o quê.
- Subagentes sempre em Opus 5.5 (`model: "opus"`). Encerrar agente assim que reporta.
- Testes completos e golden sets rodam em lote no fim de um bloco, não a cada ticket.
- Chamadas reais a Gemini, Tavily e Jev são contadas e limitadas por ticket.
- Browser para screenshot: Brave, nunca Chrome.
- Commits: `feat(NN): <slug>` por ticket, `git commit --only` com stage limpo.
