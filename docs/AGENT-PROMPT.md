# Prompt-padrão do agente executor

Você executa UM ticket do projeto `C:\Projects\desafio` (repo git, branch `main`). Windows 11, Git Bash ou PowerShell. Python 3.14 via uv, Node 24, Docker Compose.

## Leia antes de codar, nesta ordem
1. `docs/WORKFLOW.md`
2. `CONTEXT.md` (glossário: use esses termos)
3. O ticket em `.scratch/desafio/issues/NN-*.md`, incluindo a seção "Do spike" se houver
4. Os ADRs citados no ticket, em `docs/adr/`
5. `api/README.md` e a estrutura atual de `api/` (e `web/` quando existir). Leia só o que o ticket toca.
6. Se o ticket toca `web/`: `docs/UI-GUIA.md` é obrigatório, incluindo a verificação visual por screenshot.

## Regras
- Só este ticket. Não refatore o que está do lado. Não toque em `deploy/`, `docs/INFRA.md` nem `spike/`.
- TDD: teste primeiro. Testes de integração batem no Postgres do `docker-compose.yml` da raiz (porta 5433). Se ele não estiver de pé: `docker compose up --wait`.
- Durante o ticket rode só os testes do ticket (`uv run pytest tests/test_<x>.py`). A suíte completa roda em lote no fim do bloco, não é sua responsabilidade.
- Não decida arquitetura fora dos ADRs. Se precisar decidir, escolha a opção mais simples que atende o aceite, e registre em `docs/DECISOES-AUTONOMAS.md` (crie se não existir): ticket, decisão, alternativa descartada, por quê. Não pare.
- Funções marcadas `TODO(human)` no ticket: implemente você. Deixe comentário `# REVISAR(human): <o que a função decide e por quê>` acima dela. Toneli estuda depois.
- Chaves em `C:\Projects\desafio\.env`. Gemini: use `GEMINI_PAID_API_KEY`. Poucas chamadas reais; nos testes prefira resposta gravada ou modelo de teste do Pydantic AI (`TestModel`/`FunctionModel`). Se uma chave faltar, use o fallback do ticket ou registre em DECISOES-AUTONOMAS.
- Emita Evento de auditoria para toda ação relevante do ticket, via `app/audit.py`.
- Código, docstring e comentário em pt-BR, curtos.

## Ao terminar
1. `git fetch && git status`. Se `origin/main` avançou: `git pull --rebase`.
2. `git add` só dos seus arquivos. Commit: `feat(NN): <slug>` com última linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, usando `-c user.email="tonelicdtsoftware@outlook.com" -c user.name="Toneli"`. Não faça push.
3. No ticket: `**Status:** resolved` e uma seção `## Answer` de 3 a 6 linhas: o que foi feito, ressalvas, o que ficou `REVISAR(human)`.
4. Nos tickets que só dependiam deste: `**Status:** ready-for-agent`.
5. Linha em `.scratch/desafio/LEDGER.md`: `| NN | início | fim | resultado | feat(NN) |`.
6. Inclua ticket, LEDGER e DECISOES-AUTONOMAS no commit.
7. Reporte ao orquestrador em até 10 linhas: aceite cumprido ou não, hash, ressalvas, próximos tickets liberados. Sem colar código.
