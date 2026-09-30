# 04 — Workflow autônomo de desenvolvimento com Claude Code

Data da pesquisa: 2026-09-22. Host: Windows 11, Git Bash + PowerShell. Alvo de deploy: VPS Oracle Cloud Linux.
Regra do documento: cada afirmação tem URL ou caminho de arquivo. O que não foi verificado está marcado **INFERIDO**.

Abreviações de caminho usadas abaixo:
- `CACHE` = `~/.claude\plugins\cache\claude-plugins-official`
- `MPS` = `CACHE\mattpocock-skills\1.2.3`
- `RALPH` = `CACHE\ralph-loop\1.0.0`
- `SP` = `CACHE\superpowers\6.3.0` (existe também 6.4.1 no cache; o PATH aponta para 6.3.0)

---

## 1. Padrões autônomos do Claude Code em 2026

### 1.1 Ralph loop (plugin `ralph-loop`)

**O que é.** A técnica original é um loop de shell que reenvia o mesmo prompt ao agente: `while :; do cat PROMPT.md | claude-code ; done`. Fonte: https://ghuntley.com/ralph/
- Regra central: "uma coisa por loop". Estrutura de arquivos: `specs/*`, `fix_plan.md` (lista priorizada), `AGENT.md` (como buildar/rodar), `PROMPT.md`. Fonte: https://ghuntley.com/ralph/
- "Backpressure" vem de testes e build rodando depois de cada implementação. Fonte: https://ghuntley.com/ralph/

**Como o plugin funciona.** O plugin não roda um loop externo. Ele usa um **Stop hook** que bloqueia a saída da sessão e reinjeta o mesmo prompt. Fonte: `RALPH\README.md`
- Estado fica em `.claude/ralph-loop.local.md` (frontmatter com `iteration`, `max_iterations`, `completion_promise`, `session_id`). Fonte: `RALPH\hooks\stop-hook.sh`
- Comando: `/ralph-loop "<prompt>" --max-iterations N --completion-promise "TEXTO"`. Cancelar: `/cancel-ralph`. Fonte: `RALPH\README.md`

**Condições de parada.**
- `--max-iterations` (default: ilimitado). O README chama isso de "primary safety mechanism". Fonte: `RALPH\README.md`
- `--completion-promise` é match exato de string. Não aceita duas saídas (ex.: "SUCCESS" vs "BLOCKED"). Fonte: `RALPH\README.md`
- O Claude Code sobrescreve um Stop hook depois de **8 bloqueios seguidos "sem progresso"**. O teto sobe com `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`. Fonte: https://code.claude.com/docs/en/hooks-guide (seção "Stop hook hits the block cap")
- **INFERIDO:** iterações com tool use contam como progresso e não disparam o teto de 8. A doc não define "progresso" com precisão.

**Bloqueios neste host (verificados localmente).**
1. `jq` **não está** no PATH do Git Bash (`which jq` → "no jq"). O `stop-hook.sh` usa `jq` para ler `session_id` e `transcript_path`, e roda com `set -euo pipefail`. Fonte: `RALPH\hooks\stop-hook.sh`
   - **INFERIDO:** o hook morre com erro não-bloqueante, a sessão sai normalmente, e o loop nunca itera. Falha silenciosa.
2. O `hooks.json` instalado chama `bash` puro. O README do próprio plugin manda trocar para `"C:/Program Files/Git/bin/bash.exe"` no Windows, porque `bash` pode cair no WSL. Fonte: `RALPH\hooks\hooks.json`, `RALPH\README.md` (seção "Windows Compatibility")
   - A doc atual diz que hooks shell-form no Windows rodam via Git Bash. Fonte: https://code.claude.com/docs/en/hooks-guide. **INFERIDO:** o problema do WSL pode já não ocorrer nesta versão do Claude Code.

**Custo.** O README cita "$50k contract completed for $297 in API costs". Número anedótico, sem ambiente declarado. Fonte: `RALPH\README.md`, https://ghuntley.com/ralph/

**Ruim para:** decisões de design e critério de sucesso vago. Fonte: `RALPH\README.md` ("When to Use Ralph")

### 1.2 `/goal` (nativo, substituto direto do Ralph)

- Define uma condição de término. Depois de cada turno, um modelo pequeno (Haiku por default na API) avalia se a condição vale. Se não vale, o Claude começa outro turno. Fonte: https://code.claude.com/docs/en/goal
- `/goal` é um "prompt-based Stop hook" com escopo de sessão. Não depende de `jq` nem de script bash. Fonte: https://code.claude.com/docs/en/goal
- Funciona em `-p`: `claude -p "/goal <condição>"` roda o loop inteiro numa invocação. Fonte: https://code.claude.com/docs/en/goal
- Para: condição atendida, condição julgada impossível, erro que exige humano (auth, crédito esgotado, contexto que não compacta, modelo indisponível), ou vários turnos sem tool use. Fonte: https://code.claude.com/docs/en/goal
- Condição até 4.000 caracteres. Limite de turnos vai dentro do texto ("or stop after 20 turns"). Fonte: https://code.claude.com/docs/en/goal
- O avaliador **não roda comando nem lê arquivo**. Ele julga só o que apareceu na conversa. A condição precisa ser provável pela saída do próprio Claude (ex.: "`pytest` sai com 0"). Fonte: https://code.claude.com/docs/en/goal
- `/goal` não muda o modo de permissão. Para rodar sem supervisão, usar auto mode. Fonte: https://code.claude.com/docs/en/goal

### 1.3 Workflow tool / ultracode

- Workflow = script JavaScript que orquestra subagents em background. `agent()`, `pipeline()`, `parallel()`. Fonte: https://code.claude.com/docs/en/workflows
- Limites: 16 agentes concorrentes por default, 1.000 agentes por run, "No mid-run user input". Fonte: https://code.claude.com/docs/en/workflows
- Aviso de "Large workflow" acima de 25 agentes ou 1,5M tokens projetados. Com ultracode ligado, o aviso some. Fonte: https://code.claude.com/docs/en/workflows
- Ultracode = effort `xhigh` + orquestração automática de workflow em toda tarefa substantiva. "each request uses more tokens and takes longer". Fonte: https://code.claude.com/docs/en/workflows
- **O keyword `ultracode` NÃO dispara** em prompt via `-p`, prompt de SDK sem origem humana, prompt de tarefa agendada, ou payload de webhook (desde v2.1.210). Fonte: https://code.claude.com/docs/en/workflows ("Where the keyword works")
- Resume só dentro da mesma sessão (ou sessão retomada com `--resume`). Fonte: https://code.claude.com/docs/en/workflows ("Resume after a pause")
- Em `-p`, o run **não pausa** em limite de uso; o agente afetado falha. Fonte: https://code.claude.com/docs/en/workflows ("When a run hits your usage limit")

**Conclusão:** Workflow/ultracode não é a primitiva certa para "rodar enquanto durmo". Serve para fan-out dentro de uma sessão interativa (auditoria, revisão paralela, migração de muitos arquivos).

### 1.4 Routines (agentes agendados na nuvem, `/schedule`)

- Rodam em infraestrutura da Anthropic. Continuam com o laptop fechado. Research preview. Fonte: https://code.claude.com/docs/en/routines
- **Exigem repositório GitHub.** Cada run clona do branch default e empurra só para branches `claude/`. Fonte: https://code.claude.com/docs/en/routines
- Sem seletor de modo de permissão: rodam shell, skills commitadas no repo e connectors sem pedir aprovação. Fonte: https://code.claude.com/docs/en/routines
- Intervalo mínimo: 1 hora. Existe teto diário de runs por conta. One-off runs não contam no teto. Fonte: https://code.claude.com/docs/en/routines
- **INFERIDO:** o número exato do teto diário. A doc manda consultar em claude.ai/code/routines.
- Status verde = sessão saiu sem erro de infra. Não significa que a tarefa deu certo. Fonte: https://code.claude.com/docs/en/routines
- Rede default "Trusted": só allowlist de registries e domínios comuns. Fonte: https://code.claude.com/docs/en/routines

### 1.5 `claude -p` headless em loop

- `-p` roda não-interativo. Sai com 0 em sucesso e não-zero em falha. Fonte: https://code.claude.com/docs/en/headless
- `--output-format json` devolve `total_cost_usd` e `session_id`. É estimativa client-side. Fonte: https://code.claude.com/docs/en/headless
- `--max-turns N` (só print mode). `--max-budget-usd X` (só print mode, conta subagents). `--fallback-model sonnet,haiku`. Fonte: https://code.claude.com/docs/en/cli-reference
- **INFERIDO:** `--max-budget-usd` age sobre gasto estimado. Com login de assinatura (não API key), o efeito prático não foi verificado.
- `--bare` pula hooks, skills, plugins, CLAUDE.md e exige `ANTHROPIC_API_KEY`. Fonte: https://code.claude.com/docs/en/headless
  - Consequência: com `--bare`, as skills superpowers/mattpocock **não carregam**. Para usar skills, rodar sem `--bare`.
- Skills user-invoked funcionam em `-p` se o prompt contém `/nome-da-skill`. Fonte: https://code.claude.com/docs/en/headless
- Loop por tarefa é padrão documentado ("Fan out across files"): `for file in ...; do claude -p ... --allowedTools ...; done`. Fonte: https://code.claude.com/docs/en/best-practices

**Permissões sem supervisão (duas opções documentadas):**
- `--dangerously-skip-permissions` = `bypassPermissions`. Doc: "Only use this mode in isolated environments like containers, VMs, or dev containers without internet access". Não roda como root. "offers no protection against prompt injection". Fonte: https://code.claude.com/docs/en/permission-modes
- `--permission-mode auto --permission-prompts none` (v2.1.259+). Classificador revisa cada ação; o que cairia em prompt é negado. Fonte: https://code.claude.com/docs/en/headless ("Turn off permission prompts in unattended runs")
- O classificador do auto mode bloqueia o Claude de **lançar** um loop autônomo com `--dangerously-skip-permissions`. Fonte: https://code.claude.com/docs/en/permission-modes
  - Consequência: o script de loop precisa ser iniciado pelo humano, não pelo Claude.

### 1.6 GitHub Actions (`anthropics/claude-code-action@v1`)

- Modo interativo (`@claude` em issue/PR) e modo automação (`prompt:` em qualquer evento, inclusive `schedule`). Fonte: https://code.claude.com/docs/en/github-actions
- Exige repo GitHub, GitHub App instalado e secret `ANTHROPIC_API_KEY` ou `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`). Fonte: https://code.claude.com/docs/en/github-actions
- Custo = minutos de Actions + tokens. Controles: `--max-turns` em `claude_args`, timeout de workflow, concurrency. Fonte: https://code.claude.com/docs/en/github-actions
- Commits feitos com `GITHUB_TOKEN` default não disparam CI. Fonte: https://code.claude.com/docs/en/github-actions

### 1.7 Qual serve para "plano de N tarefas → TDD → verifica → commita → próxima", sem supervisão

| Opção | Roda com PC desligado | Precisa GitHub | Contexto limpo por tarefa | Bloqueio neste host |
|---|---|---|---|---|
| Ralph plugin | Não | Não | Não (mesma sessão) | `jq` ausente; `bash` no hooks.json |
| `/goal` interativo + auto mode | Não | Não | Não (compacta) | Nenhum conhecido |
| Loop `claude -p` por tarefa | Não | Não | **Sim** | Nenhum conhecido |
| Workflow/ultracode | Não | Não | Sim por agente | Não dispara de `-p`; sem input no meio |
| Routines | **Sim** | **Sim** | Sim por run | Precisa repo + setup de ambiente na nuvem |
| GitHub Actions | **Sim** | **Sim** | Sim por run | Precisa repo + secret |

Fontes: seções 1.1–1.6.

Melhor para o caso: **loop externo de `claude -p`, uma tarefa por invocação**. Motivos:
- Contexto limpo por tarefa. Fonte do motivo: "one feature per session" em https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Sem dependência de `jq` nem de GitHub.
- Parada determinística: exit code, `--max-turns`, `--max-budget-usd`, contagem de tarefas no ledger.

---

## 2. Wayfinder sem repo GitHub (tracker local-markdown)

**Regra da skill.** "If no tracker has been provided, default to the local-markdown tracker." O tracker vem de `docs/agents/issue-tracker.md`, escrito por `/setup-matt-pocock-skills`. Fonte: `MPS\skills\engineering\wayfinder\SKILL.md`, `MPS\CHANGELOG.md` (linha 197)

**Layout esperado (seção "Wayfinding operations").** Fonte: `MPS\skills\engineering\setup-matt-pocock-skills\issue-tracker-local.md`

```
.scratch/<effort>/
├── map.md                     # Destination / Notes / Decisions so far / Not yet specified / Out of scope
└── issues/
    ├── 01-<slug>.md           # Type: research|prototype|grilling|task
    ├── 02-<slug>.md           # Status: claimed|resolved
    └── ...                    # Blocked by: 01, 03
```

- **Blocking:** linha `Blocked by: NN, NN` no topo. Ticket desbloqueado quando todos os listados estão `resolved`.
- **Frontier:** arquivos abertos, desbloqueados e sem claim; menor número ganha.
- **Claim:** gravar `Status: claimed` antes de qualquer trabalho.
- **Resolve:** anexar `## Answer`, gravar `Status: resolved`, anexar ponteiro (gist + link) em "Decisions so far" do `map.md`.

Fonte das cinco regras: `MPS\skills\engineering\setup-matt-pocock-skills\issue-tracker-local.md`

**Pontos que limitam o uso aqui.**
- Wayfinder é **planejamento, não execução**: "produce decisions, not deliverables". Fonte: `MPS\skills\engineering\wayfinder\SKILL.md`
- `disable-model-invocation: true`: só o humano chama `/wayfinder`. Fonte: `MPS\skills\engineering\wayfinder\SKILL.md`
- "never resolve more than one ticket per session" (exceto research). Tickets `grilling` e `prototype` são HITL. Fonte: `MPS\skills\engineering\wayfinder\SKILL.md`
- Consequência: wayfinder não roda sozinho de madrugada. Tickets `research` e `task` (quando o agente consegue fazer sozinho) são AFK. Tickets `grilling` e `prototype` são HITL. Fonte: `MPS\skills\engineering\wayfinder\SKILL.md` ("Ticket Types")

**Tickets de execução (to-tickets, não wayfinder).** Para tarefas de implementação o formato local é outro. Fonte: `MPS\skills\engineering\to-tickets\SKILL.md`
- Arquivo: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numerado em ordem de dependência.
- Template: `**What to build:**`, `**Blocked by:**`, `**Status:** ready-for-agent`, checklist de critérios de aceite.
- Esse template **é** o "task file com acceptance criteria" da pergunta 3.

**`/setup-matt-pocock-skills` existe localmente?** Sim.
- Arquivo: `MPS\skills\engineering\setup-matt-pocock-skills\SKILL.md`. Registrado em `MPS\.claude-plugin\plugin.json` (linha 27).
- É user-invoked. Nenhuma skill consegue chamá-la. Fonte: `MPS\.agents\invocation.md`
- Grava a config em `docs/agents/` (issue tracker, triage labels, layout de docs de domínio). Fonte: `MPS\docs\engineering\setup-matt-pocock-skills.md`
- **INFERIDO:** não aparece na lista de skills desta sessão com esse nome; pode estar oculta por ser user-invoked. Testar digitando `/setup-matt-pocock-skills` ou `/mattpocock-skills:setup-matt-pocock-skills`.

---

## 3. Boas práticas para run sem supervisão seguro e retomável

### 3.1 O que a Anthropic publicou

**"Effective harnesses for long-running agents"** — https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Dois papéis: agente inicializador (cria feature list, arquivo de progresso, git init) e agente de código (progresso incremental).
- Feature list em JSON, todas começando como "failing".
- Arquivo `claude-progress.txt` + histórico git para o próximo agente entender o estado.
- Uma feature por sessão: "incremental approach turned out to be critical to addressing the agent's tendency to do too much at once".
- Verificação end-to-end obrigatória antes de marcar feature como pronta. Sem isso o Claude "would fail to recognize that the feature didn't work end-to-end".
- Falhas típicas: vitória prematura, bug não documentado, passo de init esquecido (resolver com `init.sh`).

**"Harness design for long-running application development"** (2026-03-24) — https://www.anthropic.com/engineering/harness-design-long-running-apps
- Três agentes: planner (prompt de 1–4 frases → spec), generator (uma feature por vez), evaluator (Playwright MCP, testa a app rodando).
- "Sprint contract": generator e evaluator combinam o critério de pronto antes de cada unidade.
- Autoavaliação é enviesada: "agents tend to respond by confidently praising the work—even when... the quality is obviously mediocre".
- Com Opus 4.6 o harness foi simplificado: saiu a decomposição em sprints; ficou planner + generator + evaluator no fim.
- Números reportados (Opus 4.5/4.6, stack React+Vite+FastAPI+SQLite/Postgres):

| Caso | Duração | Custo |
|---|---|---|
| Retro Game Maker, agente solo | 20 min | $9 |
| Retro Game Maker, harness completo | 6 h | $200 |
| Digital Audio Workstation, harness simplificado | 3 h 50 min | $124,70 |

**Doc de best practices** — https://code.claude.com/docs/en/best-practices
- "Give Claude a check it can run... It's the difference between a session you watch and one you walk away from."
- Gate determinístico: Stop hook que roda o check e bloqueia o fim do turno.
- Revisão adversarial por subagent em contexto limpo antes de dar como pronto. Orientar o revisor a só apontar gap de correção ou requisito, senão ele inventa achado.
- Spec auto-contida termina com passo de verificação end-to-end.
- Depois de duas correções falhas, `/clear` e prompt melhor.

### 3.2 Checklist aplicado (cada item com fonte)

1. **Task file com critério de aceite.** Template to-tickets local (seção 2). Fonte: `MPS\skills\engineering\to-tickets\SKILL.md`
2. **Uma tarefa por sessão, contexto limpo.** Fonte: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
3. **Ledger de progresso fora da conversa.** Superpowers SDD usa `.superpowers/sdd/<plan>/progress.md`; linha `Task N: complete` marca tarefa feita e não deve ser redespachada. Motivo citado: "controllers that lost their place have re-dispatched entire completed task sequences — the single most expensive failure observed". Fonte: `SP\skills\subagent-driven-development\SKILL.md`
4. **Commit por tarefa.** Fonte: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents; `MPS\skills\engineering\implement\SKILL.md` ("Commit your work to the current branch")
5. **Testes como gate.** Rodar arquivo de teste isolado durante a tarefa e suíte inteira no fim. Fonte: `MPS\skills\engineering\implement\SKILL.md`
6. **Worktree.** `claude --worktree <nome>` cria `.claude/worktrees/<nome>/` no branch `worktree-<nome>`. Fonte: https://code.claude.com/docs/en/worktrees
   - `-p --worktree` pula o trust check e **não limpa** a worktree no fim. Fonte: https://code.claude.com/docs/en/worktrees
   - No Windows, aprovações "don't ask again" ficam na worktree, não no checkout principal. Passar `--allowedTools`/`--settings` na linha de comando. Fonte: https://code.claude.com/docs/en/worktrees
   - Para execução **sequencial** de tarefas dependentes, uma worktree (ou um branch) para o run inteiro basta. Worktree por tarefa só paga quando há tarefas paralelas. **INFERIDO** (juízo, não doc).
7. **Limites de orçamento e tempo.** `--max-turns`, `--max-budget-usd`, `--fallback-model`. Fonte: https://code.claude.com/docs/en/cli-reference
8. **Anti-loop infinito.**
   - Teto de 8 bloqueios do Stop hook. Fonte: https://code.claude.com/docs/en/hooks-guide
   - `/goal` para sozinho quando não há tool use por vários turnos. Fonte: https://code.claude.com/docs/en/goal
   - SDD limita rodadas de correção a 5 (R≤3 retoma implementer; R≥4 implementer novo com modelo mais capaz). Fonte: `SP\skills\subagent-driven-development\SKILL.md`
   - No loop externo: contador de tentativas por tarefa; tarefa que falhou 2× vira `Status: blocked` e o loop segue para a próxima desbloqueada. **INFERIDO** (desenho proposto).
9. **Decisão sem parar.** SDD manda registrar `Ruling: <decisão> — <porquê> — <custo se errado>` no ledger e seguir. Só para em: ação destrutiva/irreversível, ação sensível de segurança, efeito fora da worktree (merge, push em branch compartilhado, publish), plano quebrado. Fonte: `SP\skills\subagent-driven-development\SKILL.md`
10. **Revisor separado do autor.** Fonte: https://www.anthropic.com/engineering/harness-design-long-running-apps; https://code.claude.com/docs/en/best-practices

---

## 4. Workflow concreto para este projeto

Contexto: chat app com multi-conversa, tools (web/scraping), vision, PDF, share, deploy público, persistência, auto-compactação, cap de tokens, auditoria. Fonte: `C:\Projects\desafio\DESAFIO.md`

### Fase 0 — Setup (humano, ~30 min)
1. `git init` no projeto. Worktrees exigem git. Fonte: https://code.claude.com/docs/en/worktrees
2. Instalar `jq` **só se** for usar o plugin Ralph. Caso contrário, pular.
3. Decidir auth. É uma bifurcação:
   - **API key:** paga por token; `--max-budget-usd` faz sentido. Mas `/schedule` fica oculto quando `ANTHROPIC_API_KEY` está setada. Fonte: https://code.claude.com/docs/en/routines ("Troubleshooting")
   - **Assinatura claude.ai (Pro/Max/Team/Enterprise):** Routines funcionam. Efeito de `--max-budget-usd` é **INFERIDO**.
   - **INFERIDO:** qual está em uso hoje.
4. Conferir versão: `claude --version`. A recomendação depende de `--permission-prompts none` (v2.1.259+) e do enforcement de `--max-budget-usd` (v2.1.217+). Fonte: https://code.claude.com/docs/en/headless, https://code.claude.com/docs/en/cli-reference
5. Desligar MCP quebrado no run noturno. Nesta sessão o MCP `devflow` falhou com CONNECTION_CLOSED. **INFERIDO:** cada `claude -p` sem `--bare` tenta reconectar e pode perder tempo de startup por tarefa.
6. Criar repo GitHub privado **só se** for usar Routines ou Actions (seção 1.4/1.6).

### Fase 1 — Spec (HITL, acordado)
- `superpowers:brainstorming` ou `mattpocock-skills:grilling` + `domain-modeling` → `SPEC.md` auto-contido com verificação end-to-end no fim. Fonte do formato: https://code.claude.com/docs/en/best-practices ("Let Claude interview you")
- Wayfinder só se o destino estiver nebuloso. Aqui o destino é claro (lista de requisitos fechada), então wayfinder é custo sem ganho. **INFERIDO** (juízo).

### Fase 2 — Plano em tarefas (HITL, acordado)
- `superpowers:writing-plans` gera o plano, ou `to-tickets` gera `.scratch/chat-app/issues/NN-<slug>.md`.
- Cada tarefa: fatia vertical, critérios de aceite testáveis, `Blocked by`, tamanho de uma sessão.
- **Revisão humana do plano antes de dormir.** Este é o checkpoint mais barato.

### Fase 3 — Execução autônoma (AFK, dormindo / no trabalho)
Duas variantes. Recomendo a A.

**A. Loop externo `claude -p` (recomendada).** Script em Git Bash, iniciado pelo humano:
- Para cada ticket desbloqueado em ordem: `claude -p "<prompt fixo: leia o ticket X, /tdd, rode testes, commite, atualize o ledger>" --permission-mode auto --permission-prompts none --max-turns <N> --max-budget-usd <X> --output-format json`.
- Gravar `total_cost_usd`, exit code e hash do commit no ledger.
- Checar gate fora do Claude: rodar a suíte de testes no script; se falhar, `git reset` da tarefa e marcar tentativa. **INFERIDO** (desenho proposto).
- Rodar dentro de um branch dedicado (ou `--worktree run-noite`).
- Se quiser `--dangerously-skip-permissions`: só dentro de container Docker como usuário não-root. Fonte: https://code.claude.com/docs/en/permission-modes. Docker Desktop está no PATH deste host (verificado: `/c/Program Files/Docker/Docker/resources/bin`).

**B. Uma sessão interativa deixada aberta.** Auto mode + `superpowers:subagent-driven-development` + `/goal "todo Task N do plano tem linha 'Task N: complete' no ledger e a suíte passa, ou pare após 60 turnos"`. Fonte: https://code.claude.com/docs/en/goal, `SP\skills\subagent-driven-development\SKILL.md`
- Vantagem: revisão spec+qualidade por tarefa já vem pronta no SDD.
- Desvantagem: uma sessão só; depende de compactação; se o PC dormir, para.

### Fase 4 — Checkpoints humanos
- Manhã: ler ledger + `git log --oneline` + rodar a app. Evidência em vez de afirmação. Fonte: https://code.claude.com/docs/en/best-practices
- Revisão adversarial por fatia: `/code-review` ou `mattpocock-skills:code-review` contra o spec. Fonte: https://code.claude.com/docs/en/best-practices
- Deploy na Oracle: HITL. Push, publicação e credenciais são efeitos fora da worktree. Fonte do critério: `SP\skills\subagent-driven-development\SKILL.md`

### Estimativa de custo por tarefa — **INFERIDO**

Âncora com fonte: harness Anthropic ≈ $124,70 / 3,8 h e $200 / 6 h em Opus 4.x a $5/$25 por MTok → **~$30/h** de agente. Fonte: https://www.anthropic.com/engineering/harness-design-long-running-apps, https://platform.claude.com/docs/en/about-claude/pricing

Preços por MTok (API, input / output / cache hit). Fonte: https://platform.claude.com/docs/en/about-claude/pricing

| Modelo | Input | Output | Cache hit |
|---|---|---|---|
| Fable 5.1 | $10 | $50 | $0,25 |
| Opus 5.5 | $4 | $20 | $0,20 |
| Sonnet 5 | $2 | $10 | $0,20 |
| Haiku 4.5 | $1 | $5 | $0,10 |

Modelos 4.7+ usam tokenizer que gera ~30% mais tokens para o mesmo texto. Fonte: https://platform.claude.com/docs/en/about-claude/pricing

Conta (INFERIDO): tarefa TDD de 15–30 min, 1–3M tokens de input (maioria cache hit) e 30–100k de output.
- Opus 5.5: 2M × ~$0,40 médio (mistura cache/não-cache) + 60k × $20 ≈ **$1–4 por tarefa**.
- Com revisor por tarefa (SDD): **×1,5 a ×2**.
- Fable 5.1: **×2,5** sobre Opus 5.5.
- Plano de 15–25 tarefas em Opus 5.5 com revisão: **~$40–150 no total**. Em reais: multiplicar pela cotação do dia (não verificada).
- Com assinatura em vez de API: não há cobrança por token; consome a cota do plano. **INFERIDO:** quantas tarefas cabem numa janela de cota.

Antes de rodar tudo: **sonda barata** com 1–2 tarefas, ler `total_cost_usd` do JSON, e só então extrapolar. Fonte do método: https://code.claude.com/docs/en/best-practices ("Test on a few files, then run on all of them"), https://code.claude.com/docs/en/workflows ("run the workflow on a small slice first")

---

## Recomendação

1. **Primitiva de execução:** loop externo de `claude -p`, uma tarefa por invocação, iniciado por você. Não usar Ralph plugin neste host sem antes instalar `jq` e ajustar o `hooks.json`. Não usar Workflow/ultracode como motor noturno: o keyword não dispara de `-p` e não há input no meio.
2. **Permissão:** `--permission-mode auto --permission-prompts none`. `--dangerously-skip-permissions` só dentro de Docker, usuário não-root.
3. **Limites em toda invocação:** `--max-turns`, `--max-budget-usd`, `--fallback-model`, `--output-format json`. Contador de tentativas por tarefa no script.
4. **Tarefas:** template to-tickets local em `.scratch/<feature>/issues/NN-<slug>.md`, com `Blocked by` e checklist de aceite. Wayfinder fica de fora: o destino já é claro e ele não executa.
5. **Estado:** ledger em arquivo + commit por tarefa. O script lê o ledger para retomar.
6. **Gate:** suíte de testes rodada pelo script, fora do Claude. Tarefa só vira `complete` com exit 0.
7. **Revisão:** revisor em contexto limpo por tarefa; você revisa ledger + `git log` + app rodando de manhã.
8. **Cloud (Routines/Actions):** só se precisar rodar com o PC desligado. Ambos exigem repo GitHub. Routines têm intervalo mínimo de 1 h e teto diário de runs.
9. **Antes do run inteiro:** sonda com 1–2 tarefas, medir custo real, extrapolar, pedir autorização. Estimativa INFERIDA: $1–4 por tarefa em Opus 5.5 sem revisor.
