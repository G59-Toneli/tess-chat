# Handoff do orquestrador

Atualizado em 2026-09-23 ~03:20 (horário local -03:00). Sessão atual: orquestrador Fable (a5f6122f), recebeu handoff de `desafio-a7` às 02:45.

## Como orquestrar (ciclo)
1. Escolher ticket `ready-for-agent` cujos `Blocked by` estão `resolved`.
2. Disparar `Agent` com `model: "opus"`, `subagent_type: "general-purpose"`, nome `exec-NN`. Prompt curto: "Execute o ticket NN seguindo à letra docs/AGENT-PROMPT.md" + contexto de 3 a 6 linhas (o que já existe, quem edita o quê em paralelo, número da próxima migração, teto de chamadas reais).
3. Agente reporta → conferir `git log origin/main..HEAD` → `git push` → `TaskStop` no agente → disparar o próximo.
4. Ticket de front: abrir 1 ou 2 screenshots de `.scratch/desafio/screens/` e aprovar ou abrir ticket de ajuste. Toneli não revisa tela.
5. Notificações repetidas de agente (idle_notification) não trazem nada novo: ignorar.
6. Itens que precisam do Toneli vão em `MANHA.md`.

## Regras aprendidas na noite
- **Stage é compartilhado.** Vários agentes no mesmo working tree. Commit sempre com `--only <arquivos>`. Um commit meu engoliu os arquivos do ticket 06 (ficaram em 2c738a6).
- **`api/app/chat.py` é o gargalo.** Só um agente por vez editando o laço do Agent. Tickets que só montam prompt ou adicionam endpoint podem correr em paralelo se limitarem a região.
- **Migrações:** informar no prompt o número da próxima (`0011` é a próxima livre após 0010; conferir `ls api/migrations/versions`). Dois agentes em paralelo não podem criar migração. Se acontecer, o commit da base entra antes no push.
- **Playwright MCP abre o Chrome.** Agentes contornam com `playwright-core` apontando pro executável do Brave. Porta 5173 pode estar ocupada por outro app; usar porta própria.
- **Gemini free key** (`GEMINI_API_KEY`) não serve. Sempre `GEMINI_PAID_API_KEY`.
- Tetos de chamada real por ticket: Gemini 2 a 4, Tavily 2 a 3, Jev ~10. Agentes às vezes estouram porque um turno faz vários requests. Aceitável, registrado.
- Rate limit do plano Max: esperar e repetir.

## Estado dos tickets
- **Resolvidos:** 01, 03, 04, 05, 06, 06b, 07a, 07, 07b, 07c, 08, 09, 09b, 10, 11, 12, 13, 14, 15, 18 (parte AFK), 20, 22. Tudo em `origin/main`.
- **Rodando:** exec-17 (MCP; migração 0013; único em `chat.py`/`tools.py`).
- **Próximos, nesta ordem:** 21 (suíte completa em lote + regressões listadas no ticket; roda depois do 17) → 19 (README, guia de entrevista, roteiro do vídeo; lê `docs/MOTIVACOES.md`, `docs/ESTRUTURA.md`, `docs/LACUNAS.md`). 16 (deploy) quando o Toneli entregar SSH.
- **Tickets novos desta sessão:** 20 (estrutura do repo + motivações, resolvido), 21 (suíte em lote), 22 (WORKFLOW.md reflete a prática, resolvido).
- **Bloqueados em Toneli:** 02 e 16 (SSH do VPS, registro A). Validação manual do 18 com a conta Google está no `MANHA.md`.
- 17 e 18 foram liberados para rodar em localhost sem esperar o 16; deploy só troca a URL base (`PUBLIC_BASE_URL`).
- Próxima migração livre depois do 17: `0014` (conferir `ls api/migrations/versions`).

## Lacunas conhecidas
Consolidadas em `docs/LACUNAS.md`. Ticket 19 lê. Duas pedem decisão: reserva por `count_tokens` (ADR 0004 vs código) e cobrança do turno cortado pelo teto de tools.

## Marco
Camada 1 no ar até sexta 26/09. Prazo final terça 29/09 12h, confirmado com o CPO.

## Golden set e evals
Golden set do Jev já gravado em `api/tests/fixtures/jev_golden.json` (10 casos, 9/9, caso 10 ambíguo abaixo do limiar). Fixture autouse desliga o Jev nos testes. Não regravar. Rodar a suíte completa só no fim do bloco.

## Memória do Claude (fora do repo)
Regras do Toneli também estão em `C:\Users\Admin\.claude\projects\C--Projects-desafio\memory\`: Opus nos subagentes, defender decisões, modo autônomo e custo, preferências de UI, Brave, matar agentes idle.
