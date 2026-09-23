# Workflow de execução autônoma

Base: `research/04-workflow-autonomo-dev.md`.

## Regras
- Um ticket por invocação de `claude -p --model opus`. Nunca dois.
- Antes de codar, o agente lê `CONTEXT.md`, o ticket e os ADRs referenciados.
- TDD (`mattpocock-skills:tdd`). Testes rodam **fora** do Claude, no script, como gate. Só exit 0 fecha o ticket.
- Um commit por ticket, mensagem `feat(NN): <slug>`.
- Ledger em `.scratch/desafio/LEDGER.md`: uma linha por tentativa: ticket, início, fim, resultado, commit, turnos.
- Decisão não coberta por ADR: escolher a opção mais simples que atende o aceite e registrar em `docs/DECISOES-AUTONOMAS.md`. Não parar.
- `TODO(human)`: desde 23/09 à noite o agente implementa e marca `REVISAR(human)`. Toneli estuda depois. Nada bloqueia.
- Rate limit do plano Max: o script espera 30 min e tenta de novo. Não é falha do ticket.
- Limites por invocação: `--max-turns 80`, `--permission-mode auto --permission-prompts none --output-format json`.
- Sonda feita (01 e 03). Prompt-padrão em `docs/AGENT-PROMPT.md`. Suíte completa e golden set rodam em lote no fim de cada bloco.

## Checkpoint humano (manhã / almoço)
1. `git log --oneline` e `LEDGER.md`.
2. Subir a app e clicar no fluxo do ticket.
3. Resolver `waiting-human` e `BLOCKED`.
