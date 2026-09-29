# Handoff do orquestrador

## Etapa 2: Ligação (voz + tela), aberta em 28/09 ~23:00
- Pedido da Tess: conversa por voz com o agente e compartilhamento de tela durante a ligação. Entrega até **qua 30/09 23h59**: repositório, vídeo de demo, vídeo de arquitetura.
- Decisões do grilling de 28/09: ADR 0026, 0027, 0028; contrato em `docs/PROTOCOLO-LIGACAO.md`; termos Ligação, Ticket de Ligação e Frame no `CONTEXT.md`.
- Tickets 75 a 81. Ordem: 75 (spike) → 76 (back) ∥ 78 (front) → 77 (histórico) ∥ 79 (nginx) → 80 (E2E + smoke) → 81 (estudo + roteiro).
- Modo: 100% autônomo. Cada ticket registra "Paradas de estudo"; o 81 consolida em `docs/ESTUDO-VOZ.md`. O Toneli só estuda (trabalha 8h às 18h).
- Teto de gasto da etapa: R$ 30. Teto de chamadas reais: 10 sessões de até 2 min. Chave `GEMINI_LIVE_API_KEY` = free (`GEMINI_API_KEY`); se a free não servir no Live, usar a paga sem perguntar.
- Corte de escopo: qua 30/09 18h é código congelado. Primeiro a cair: 77.
- Autorizado: o agente do 79 aplica o nginx no VPS (backup, `nginx -t`, reload, só o site `tess-chat`).
- Pendente com o Toneli: sessão guiada sobre Jev e MCP (perguntas que ele não respondeu na entrevista).
- **29/09 ~10:20:** 75 a 82 resolvidos e em produção. Estudo em `docs/ESTUDO-VOZ.md` (23 paradas), roteiro em `docs/ROTEIRO-VIDEOS.md`. Chamadas reais: 7 de 10, R$ 0. Subagentes agora em Sonnet 5.5 (pedido do Toneli, 29/09).
- Em aberto: latência 1,9 s em produção vs 0,5 s local (causa não isolada); reserva de crédito só compara, não segura saldo (`LACUNAS.md`); barra `chart-4` da Ligação quase invisível no dark; conta demo não entra em produção.

Atualizado em 2026-09-23 ~13:40. Sessão encerrada a pedido do Toneli; retomar a partir daqui (horário local -03:00). Sessão atual: orquestrador Fable (a5f6122f), recebeu handoff de `desafio-a7` às 02:45.

## Como orquestrar (ciclo)
1. Escolher ticket `ready-for-agent` cujos `Blocked by` estão `resolved`.
2. Disparar `Agent` com `model: "opus"`, `subagent_type: "general-purpose"`, nome `exec-NN`. Prompt curto: "Execute o ticket NN seguindo à letra docs/AGENT-PROMPT.md" + contexto de 3 a 6 linhas (o que já existe, quem edita o quê em paralelo, número da próxima migração, teto de chamadas reais).
3. Agente reporta → conferir `git log origin/main..HEAD` → `git push` → `TaskStop` no agente → disparar o próximo.
4. Ticket de front: abrir 1 ou 2 screenshots de `.scratch/desafio/screens/` e aprovar ou abrir ticket de ajuste. Toneli não revisa tela.
5. Notificações repetidas de agente (idle_notification) não trazem nada novo: ignorar.
6. Itens que precisam do Toneli: reportar direto a ele no chat.

## Regras aprendidas na noite
- **Stage é compartilhado.** Vários agentes no mesmo working tree. Commit sempre com `--only <arquivos>`. Um commit meu engoliu os arquivos do ticket 06 (ficaram em 2c738a6).
- **`api/app/chat.py` é o gargalo.** Só um agente por vez editando o laço do Agent. Tickets que só montam prompt ou adicionam endpoint podem correr em paralelo se limitarem a região.
- **Migrações:** informar no prompt o número da próxima (`0011` é a próxima livre após 0010; conferir `ls api/migrations/versions`). Dois agentes em paralelo não podem criar migração. Se acontecer, o commit da base entra antes no push.
- **Playwright MCP abre o Chrome.** Agentes contornam com `playwright-core` apontando pro executável do Brave. Porta 5173 pode estar ocupada por outro app; usar porta própria.
- **Gemini free key** (`GEMINI_API_KEY`) não serve. Sempre `GEMINI_PAID_API_KEY`.
- Tetos de chamada real por ticket: Gemini 2 a 4, Tavily 2 a 3, Jev ~10. Agentes às vezes estouram porque um turno faz vários requests. Aceitável, registrado.
- Rate limit do plano Max: esperar e repetir.
- **Agentes conversam entre si e ressuscitam.** Depois do `TaskStop`, um agente que recebe mensagem de outro volta a rodar. Conferir com `ListAgents` e encerrar de novo. Não deixe dois agentes com interesse no mesmo arquivo (`.env.example`) vivos ao mesmo tempo.
- **Dois agentes em `web/` funcionam** se o prompt particionar por arquivo: um cria página + rota + link no nav, o outro só componente existente. Funcionou em 14 + 07c.
- **Tickets só de docs correm em paralelo com qualquer ticket de código** (20, 22, 24). Bom uso da fila enquanto `chat.py` está ocupado.
- **Push na `main` publica em produção** (CI desde 23/09 ~13:00). Todo agente roda a suíte do aceite antes de commitar; o orquestrador espera o run (`gh run watch`) depois do push.
- **A API local da 8000 roda sem `--reload`.** Mudança de back exige restart (PowerShell: matar o processo na 8000 e `uv run uvicorn app.main:app --port 8000` em `api/`). Mudança só de front: `npm run build` basta. Agentes não reiniciam a 8000; sobem API própria em outra porta (8001 a 8006 já usadas) e avisam.
- **Não perder a `CONNECTORS_KEY` do `.env`.** Em 23/09 ela sumiu numa edição manual; foi regenerada e Google/Stripe tiveram de ser recadastrados. Antes de reiniciar a 8000, `grep -c ^CONNECTORS_KEY= .env`.
- **Agente não altera a Configuração da conta demo** (modelo, limiares, cap) sem reverter no fim. Um flash-lite esquecido na conta mascarou o Stripe por três tickets.
- **Modelo importa para tools MCP genéricas.** flash-lite escolhe a tool errada (planner) no Stripe; 3.8-flash acerta. Schema aberto de MCP vira string JSON para o Gemini (ticket 35).
- **Browser para o orquestrador:** extensão Claude in Chrome com dois browsers conectados; o Brave local é o que enxerga `127.0.0.1:8000` do tess-chat (o outro vê o outro projeto na mesma porta). Conferir com `navigator.brave` e o título da página.
- **DNS do Registro.br:** alteração de zona em domínio novo leva ~2 h para publicar. O autoritativo `a.auto.dns.br` é a fonte da verdade; testar antes de concluir.

## Estado dos tickets
- **Resolvidos:** 01, 03, 04, 05, 06, 06b, 07a, 07, 07b, 07c, 08, 09, 09b, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 (AFK), 20 a 37. Tudo em `origin/main` e em produção.
- **CI ligado (23/09 ~13:00):** push na `main` → GitHub Actions → ssh com chave própria do CI (`<omitido>`, só no VPS e nos secrets) → `deploy.sh`. Deploy key read-only cadastrada; `/opt/tess-chat` é clone git. Não precisa mais de `git archive`.
- **Stripe MCP validado com a frase do Toneli** depois dos tickets 35 e 36 e de voltar o modelo da conta demo ao padrão (um agente tinha deixado flash-lite na conta; flash-lite escolhe mal a tool).
- **Regra nova:** agente NÃO altera a Configuração da conta demo (modelo, limiares) sem reverter no fim do ticket.
- **Produção:** https://chat.toneli.dev.br no ar (VPS compartilhado, nginx do host + certbot, ADR 0014). Deploy manual: `git archive HEAD | ssh ... tar -x -C /opt/tess-chat` e `bash /opt/tess-chat/deploy/deploy.sh` (runbook em `docs/INFRA.md`). CI funcionando.
- **Tickets da manhã de 23/09 (pedidos do Toneli):** 25 e-mail com confirmação, 26 e 27 UI/UX, 28 nav + descricao_usuario, 29 conta Google + erros do Gmail, 30 teto de tools visível/configurável, 31 e 33 erro de tool MCP e args do Stripe, 32 indicador de contexto. Stripe MCP validado ponta a ponta (link de pagamento real em sandbox).
- **Chave Fernet regenerada** em 23/09 ~11:50 (a antiga se perdeu do .env local); Google e Stripe do demo local foram recadastrados.
- **Rodando:** nenhum. Todos os agentes encerrados.
- **Responsivo (23/09 noite):** 62 a 67 resolvidos e em produção. Corte em md, script `web/scripts/checar-responsivo.mjs` é o aceite de todo ticket de front. Checagem contra produção pendente: a senha da demo em prod não é a do `.env` do VPS.
- **Suíte final do bloco (23/09 ~03:45, Postgres 5433 + mcp-demo 8765):** `uv run pytest` 141 passed / 0 failed; `npm run build` e `tsc --noEmit` limpos.
- **Bloqueios do Toneli (resolvidos em 24/09):** SSH do VPS e registro A (02 e 16), validação do Conector Google (18), vídeo (19). Fallback OpenAI decidido no ADR 0018.
- **Próximo ticket de código:** 16 (deploy), assim que houver SSH. No deploy: `ENV=prod`, `PUBLIC_BASE_URL=https://chat.toneli.dev.br`, `CONNECTORS_KEY` própria, trocar `GITHUB_PAT` e recadastrar o GitHub em `/mcp`.
- Próxima migração livre: `0019`.
- **Acesso ao VPS:** chave em `<omitido>` (origem `<omitido>`, leia `LEIA.txt` antes de qualquer comando). Chave do CI em `<omitido>`. Stack em `/opt/tess-chat`, app em `127.0.0.1:8010`, nginx do host com certbot. VPS é produção compartilhada: nunca tocar em nada fora de `/opt/tess-chat` e do site nginx `tess-chat`.
- **Candidatos a próximo passo (não abertos como ticket):** propostas restantes em `docs/UX-AUDITORIA.md`; tela `/mcp` ainda mostra a descrição técnica das tools; tempo do indicador de trabalhando zera a cada espera (37); tools de leitura do Gmail ainda devolvem erro cru ao modelo (29); teste de timeout MCP de 15 s ausente (30).
- 25 (responder e-mail com confirmação, ADR 0013) foi pedido pelo Toneli às ~07:00 e fechou. HITL dele (escopo `gmail.send` no GCP, reconectar, validar) feito.
- Tickets criados nesta sessão: 20 (estrutura + motivações), 21 (suíte em lote), 22 (WORKFLOW real), 23 (resiliência MCP + SSRF), 24 (docs atualizados). Todos resolvidos.

## Lacunas conhecidas
Consolidadas em `docs/LACUNAS.md`. Ticket 19 lê. Duas pedem decisão: reserva por `count_tokens` (ADR 0004 vs código) e cobrança do turno cortado pelo teto de tools.

## Marco
Camada 1 no ar até sexta 26/09. Prazo final terça 29/09 12h, confirmado com o CPO.

## Golden set e evals
Golden set do Jev já gravado em `api/tests/fixtures/jev_golden.json` (10 casos, 9/9, caso 10 ambíguo abaixo do limiar). Fixture autouse desliga o Jev nos testes. Não regravar. Rodar a suíte completa só no fim do bloco.

## Memória do Claude (fora do repo)
Regras do Toneli também estão em `C:\Users\Admin\.claude\projects\C--Projects-desafio\memory\`: Opus nos subagentes, defender decisões, modo autônomo e custo, preferências de UI, Brave, matar agentes idle.
