# 22 — WORKFLOW.md e map.md refletem a prática, não o plano

**Type:** task (AFK, só docs)
**Status:** resolved
**Blocked by:** 20
**Refs:** `docs/WORKFLOW.md`, `.scratch/desafio/map.md`, `.scratch/desafio/HANDOFF.md`, `docs/AGENT-PROMPT.md`, `docs/MOTIVACOES.md`, `docs/ESTRUTURA.md`, `LEDGER.md`.

**Problema (achado do ticket 20):** `docs/WORKFLOW.md` descreve o plano original (loop `claude -p`, gate externo, `--max-turns`, status `BLOCKED`/`waiting-human`). A prática real desde 22/09 à noite é: uma sessão orquestradora do Claude Code (Fable) dispara agentes executores (Opus 5.5, `Agent` tool) por ticket, um por vez em `chat.py`, com stage compartilhado e `git commit --only`; o orquestrador confere o commit, dá push, encerra o agente, aprova screenshots; `REVISAR(human)` no lugar de `TODO(human)`; `HANDOFF.md` passa o estado entre sessões; `MANHA.md` lista o que precisa do Toneli. Avaliadores vão ler isso para entender o fluxo de IA. Toneli vai defender em entrevista.

**What to build:**
1. Reescrever `docs/WORKFLOW.md`: seção "Como foi de fato" (o ciclo acima, com as regras aprendidas do HANDOFF: stage compartilhado, `chat.py` como gargalo, numeração de migração no prompt, tetos de chamada real, Brave/playwright-core) e seção curta "Plano original e por que mudou" (o loop `claude -p` foi descartado: motivo INFERIDO se não estiver documentado; verifique `research/04-workflow-autonomo-dev.md`, `LEDGER.md` e `DECISOES-AUTONOMAS.md` antes de afirmar).
2. Atualizar `.scratch/desafio/map.md`: status atual dos tickets (resolvidos: 01, 03–15 exceto 02 e 16, 07a/b/c, 06b, 09b se já fechou, 20; bloqueados em Toneli: 02, 16), remover status que não existem mais.
3. Não mexer em `AGENT-PROMPT.md` (é o contrato vivo dos agentes) nem em `HANDOFF.md` (é do orquestrador).

**Aceite:**
- [ ] Alguém que leia só `WORKFLOW.md` entende como um ticket vira commit hoje, sem citar comando que não é mais usado como se fosse.
- [ ] `map.md` não contradiz `LEDGER.md`.

## Answer

- `docs/WORKFLOW.md` reescrito: papéis, ciclo de 12 passos de ticket a push, regras aprendidas do HANDOFF, estado entre sessões, e seção "Plano original e por que mudou".
- Motivo da troca do loop `claude -p` pela sessão orquestradora: INFERIDO. Nenhum doc registra; nenhum script de loop foi commitado. Se a sonda 01/03 rodou por `Agent`: também INFERIDO.
- Correção de data: a regra `REVISAR(human)` é de 22/09 22:24 (`bd7ddf6`), não 23/09.
- `map.md`: Notes sem `BLOCKED` nem `TODO(human)` bloqueante; seção "Estado dos tickets" alinhada ao LEDGER; 17 e 18 prontos para localhost; 09b resolvido (`7d5e844`).
- Nada ficou `REVISAR(human)`. Zero mudança em `api/` e `web/`.
