# Workflow de execução por agentes

Como um ticket vira commit neste repo. Fontes: `LEDGER.md`, `docs/AGENT-PROMPT.md`, `docs/MOTIVACOES.md`.

## Como foi de fato (desde 22/09 à noite)

### Papéis
- **Orquestrador:** uma sessão interativa do Claude Code (modelo Fable). Escolhe o ticket, dispara o agente, confere o commit, dá push, aprova screenshot. Não escreve código de ticket.
- **Agente executor:** um subagente Opus 5.5 disparado pela tool `Agent` do Claude Code, nome `exec-NN`. Executa um ticket só, seguindo `docs/AGENT-PROMPT.md`.
- **Toneli:** resolve o que só humano resolve (chaves, DNS, SSH), listado em `.scratch/desafio/MANHA.md`.

### Ciclo de um ticket
1. O orquestrador escolhe um ticket `ready-for-agent` com todos os `Blocked by` em `resolved`.
2. O orquestrador dispara o agente com prompt curto: "Execute o ticket NN seguindo à letra docs/AGENT-PROMPT.md", mais 3 a 6 linhas de contexto. O contexto diz o que já existe, quem edita o quê em paralelo, o número da próxima migração e o teto de chamadas reais.
3. O agente lê `WORKFLOW.md`, `CONTEXT.md`, o ticket, os ADRs citados e só o código que o ticket toca. Ticket de front lê também `docs/UI-GUIA.md`.
4. O agente faz TDD e roda só os testes do ticket, contra o Postgres do `docker-compose.yml` (porta 5433). A suíte completa não é dele.
5. Decisão fora dos ADRs: o agente escolhe a opção mais simples que atende o aceite, registra em `docs/DECISOES-AUTONOMAS.md` e segue. Não para.
7. Ticket de front: o agente tira screenshots no Brave (dark, 1440x900) e salva em `.scratch/desafio/screens/`.
8. O agente fecha o ticket: `**Status:** resolved`, seção `## Answer`, libera os tickets dependentes, escreve uma linha no `LEDGER.md`.
9. O agente commita `feat(NN): <slug>` com `git commit --only <seus arquivos>`. Não dá push.
10. O agente reporta em até 10 linhas: aceite, hash, ressalvas, tickets liberados.
11. O orquestrador confere `git log origin/main..HEAD`, dá `git push` e encerra o agente (`TaskStop`). Em ticket de front, abre 1 ou 2 screenshots e aprova ou abre ticket de ajuste.
12. O orquestrador dispara o próximo ticket.

### Regras aprendidas na execução
- **Stage compartilhado.** Vários agentes usam o mesmo working tree e o mesmo index. Todo commit usa `git commit --only` com os próprios arquivos. Antes, `git diff --cached --name-only` deve listar só esses arquivos. Motivo: um commit do orquestrador engoliu os arquivos do ticket 06 (`2c738a6`).
- **`api/app/chat.py` é o gargalo.** Só um agente por vez edita o laço do Agent. Ticket que só monta prompt, adiciona endpoint ou toca só `web/` pode correr em paralelo.
- **Migração numerada no prompt.** O orquestrador informa o número da próxima migração livre (conferir `api/migrations/versions`). Dois agentes em paralelo não criam migração.
- **Teto de chamada real por ticket.** Gemini 2 a 4, Tavily 2 a 3, Jev cerca de 10. Testes usam resposta gravada ou `TestModel`/`FunctionModel` do Pydantic AI. O LEDGER registra quantas chamadas cada ticket fez. Estouro pequeno é aceito e registrado.
- **Gemini sempre com `GEMINI_PAID_API_KEY`.** A chave free não serve.
- **Screenshot no Brave, nunca no Chrome.** O Playwright MCP abre o Chrome. Os agentes usam `playwright-core` apontando para o executável do Brave, numa porta própria (a 5173 pode estar ocupada).
- **Rate limit do plano Max:** esperar e repetir. Não é falha do ticket.
- **Testes em lote.** Suíte completa (`cd api && uv run pytest`; `cd web && npm run build`) e golden set rodam no fim de um bloco de tickets, com um agente para corrigir regressões. O golden set do Jev já está gravado e não é regravado.
- **Nada bloqueia a noite.** Decisão nova vai para `DECISOES-AUTONOMAS.md`. Regra desde 22/09 22:24 (`bd7ddf6`).

### Estado entre sessões
- `.scratch/desafio/LEDGER.md`: uma linha por execução de ticket, com início, fim, resultado e commit.
- `.scratch/desafio/MANHA.md`: o que precisa do Toneli.
- `.scratch/desafio/map.md`: destino, decisões e estado dos tickets.

## Plano original e por que mudou

- **Plano** (`research/04-workflow-autonomo-dev.md`): script em Git Bash iniciado pelo Toneli, chamando `claude -p --model opus` um ticket por invocação, com `--max-turns 80` e `--permission-mode auto`. A suíte de testes rodava fora do Claude como gate; só exit 0 fechava o ticket. Ticket que falhasse 2 vezes virava `blocked`. Decisão nova gravava `BLOCKED` no ledger e parava.
- **O que aconteceu:** o script de loop nunca foi commitado no repo. Os tickets do LEDGER rodaram pela sessão orquestradora com a tool `Agent`. Se a sonda (tickets 01 e 03) também rodou assim: **INFERIDO**, nenhum doc registra.
- **Por que mudou:** **INFERIDO**. Nenhum doc registra o motivo. Hipóteses: a sessão orquestradora roda tickets independentes em paralelo, e corrige o rumo entre um ticket e outro (contexto no prompt, ticket de ajuste) sem reiniciar um script.
- **O que se perdeu:** o gate externo. Hoje o agente roda os próprios testes e o orquestrador confia no relatório e no LEDGER. A compensação é a suíte completa em lote no fim do bloco.
- **Por que `BLOCKED` saiu:** "nada bloqueia a noite". A troca foi velocidade agora e estudo depois (`docs/MOTIVACOES.md`, seção workflow; commit `bd7ddf6`).
