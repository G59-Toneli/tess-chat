# 20 — Estrutura do repo e documento de motivações

**Type:** task (AFK, só docs)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** todos os `docs/adr/`, `CONTEXT.md`, `docs/WORKFLOW.md`, `docs/AGENT-PROMPT.md`, `docs/DECISOES-AUTONOMAS.md`, `docs/LACUNAS.md`.

**Contexto:** a estrutura do repo precisa deixar claro o fluxo de trabalho com IA. O Toneli vai se contextualizar depois fazendo perguntas ao Claude Code sobre o repo. Cada decisão precisa ter o porquê registrado. Pedido de 23/09 de madrugada.

**What to build:**
1. `docs/MOTIVACOES.md`: para cada escolha, o porquê e a alternativa descartada. Cobrir: stack (Python 3.14 + uv, FastAPI, Pydantic AI, Postgres, Alembic, React + Vite + shadcn, Gemini, Tavily, Jina/trafilatura, Jev), estilo arquitetural (nomear com precisão: monólito modular, camadas, o que é e o que não é; onde fica a fronteira entre API, domínio e infra), padrões (registro de tools, ledger de crédito, Roteador, compactação, auditoria por evento), infraestrutura (VPS + Docker Compose + Caddy/HTTPS, por que não serverless/k8s), fluxo de trabalho com IA (tickets em `.scratch/desafio/issues`, orquestrador + agentes executores, ADRs, `REVISAR(human)`, `DECISOES-AUTONOMAS`, LEDGER, golden set). Só afirme o que está no código ou nos ADRs; o que for inferido, marque `INFERIDO`. Onde um ADR já explica, linke e resuma em 2 linhas, não duplique.
2. `docs/ESTRUTURA.md`: árvore comentada do repo (1 linha por pasta/arquivo relevante) e o mapa "onde mora cada conceito do CONTEXT.md".
3. Revisar a estrutura em si: apontar (não mover) o que está fora de lugar ou faltando para o fluxo de IA ficar claro. Só mover/renomear se for trivial e não quebrar import nem referência em doc; qualquer outra sugestão vai numa seção "Sugestões" no final de `ESTRUTURA.md` para o ticket 19 decidir.
4. Adicionar em `CLAUDE.md` da raiz uma linha apontando para os dois docs. O ticket 19 (README, perguntas e respostas sobre as decisões) lê ambos.

**Aceite:**
- [ ] `docs/MOTIVACOES.md` responde "por que X e não Y" para stack, arquitetura, infra e workflow, sem contradizer nenhum ADR.
- [ ] `docs/ESTRUTURA.md` cobre toda pasta de primeiro e segundo nível do repo (exceto `node_modules`, `.venv`, caches).
- [ ] Zero mudança em código de `api/` e `web/`.

## Answer
- `docs/ESTRUTURA.md`: árvore comentada de toda pasta de 1º e 2º nível, tabelas de `api/app/`, `web/src/` e migrações, mapa conceito para módulo, tabela, tela e ADR, inventário de `REVISAR(human)`, 8 sugestões para o ticket 19.
- `docs/MOTIVACOES.md`: por que X e não Y para stack, estilo arquitetural (monólito modular por conceito, não camadas nem hexagonal), padrões, infra e workflow. Sem fonte e marcados INFERIDO: Python 3.14, uv, Alembic, SQLite como alternativa, Tavily sobre Serper, não serverless nem k8s, troca do loop `claude -p` pelo orquestrador.
- Nada movido nem renomeado. Achado principal: `WORKFLOW.md` e `map.md` descrevem o plano original, não a prática (orquestrador com agentes em paralelo, REVISAR(human) em vez de BLOCKED).
- Configuração do ticket 14 documentada pelo commit `39ddacf`. Zero mudança em `api/` e `web/`.
