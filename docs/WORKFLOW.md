# Workflow de execução autônoma

Base: `research/04-workflow-autonomo-dev.md`.

## Regras
- Um ticket por invocação de `claude -p --model opus`. Nunca dois.
- Antes de codar, o agente lê `CONTEXT.md`, o ticket e os ADRs referenciados.
- TDD (`mattpocock-skills:tdd`). Testes rodam **fora** do Claude, no script, como gate. Só exit 0 fecha o ticket.
- Um commit por ticket, mensagem `feat(NN): <slug>`.
- Ledger em `.scratch/desafio/LEDGER.md`: uma linha por tentativa: ticket, início, fim, resultado, commit, turnos.
- Decisão de arquitetura não coberta por ADR: gravar `BLOCKED: <pergunta>` no ledger e encerrar. Não decidir.
- `TODO(human)` num ticket HITL: o agente escreve testes e esqueleto, deixa o TODO, marca `waiting-human` e encerra.
- Rate limit do plano Max: o script espera 30 min e tenta de novo. Não é falha do ticket.
- Limites por invocação: `--max-turns 80`, `--permission-mode auto --permission-prompts none --output-format json`.
- Sonda: rodar tickets 01 e 03 primeiro, ler turnos e tempo, só então soltar o resto.

## Checkpoint humano (manhã / almoço)
1. `git log --oneline` e `LEDGER.md`.
2. Subir a app e clicar no fluxo do ticket.
3. Resolver `waiting-human` e `BLOCKED`.
