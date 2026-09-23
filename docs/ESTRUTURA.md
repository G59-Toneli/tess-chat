# Estrutura do repo

Mapa do repo para quem chega agora: avaliador ou o próprio Toneli antes da entrevista. Os porquês ficam em `docs/MOTIVACOES.md`. Os termos seguem o `CONTEXT.md`.

Retrato de 2026-09-23, depois do ticket 54 (commit `b255961`). Revisado na revisão final.

## Árvore comentada

Uma linha por pasta ou arquivo relevante. `node_modules`, `.venv`, `__pycache__` e `dist` ficam de fora.

```
.
├── README.md                 porta de entrada: o que é, arquitetura, como rodar, decisões, limites (ticket 19)
├── CLAUDE.md                 instruções fixas para qualquer sessão do Claude Code neste repo
├── CONTEXT.md                glossário do domínio: um significado por termo
├── DESAFIO.md                enunciado original do desafio (e-mail do CPO)
├── Dockerfile                multi-stage: build do front (Node) e imagem da API (Python) servindo web/dist
├── docker-compose.yml        dev local: Postgres 17 na porta 5433 e servidor MCP de demo (`mcp-demo`) na 8765
├── .dockerignore             tira spike/, research/, .scratch/ e segredos da imagem
├── .gitignore                ignora .env, data/, .venv, node_modules, dist, .playwright-mcp
├── .gitattributes            fim de linha LF
├── .env                      chaves e URLs de banco. Fora do git; o avaliador não vê
├── .env.example              modelo versionado do .env, uma linha por campo de `Settings` (ticket 19)
│
├── api/                      backend: FastAPI + Pydantic AI + SQLAlchemy async
│   ├── README.md             como subir o banco, migrar, testar e rodar a API
│   ├── pyproject.toml        dependências (uv); pytest em modo asyncio
│   ├── uv.lock               lock das dependências Python
│   ├── .python-version       Python 3.14
│   ├── alembic.ini           config do Alembic
│   ├── app/                  código da API: um módulo por conceito do glossário (lista abaixo)
│   ├── migrations/           Alembic: versions/0001..0020, uma por ticket que mudou o schema
│   └── tests/                testes de integração contra o Postgres real; fixtures/ guarda respostas gravadas
│
├── web/                      front: React 19 + Vite + Tailwind + shadcn + AI Elements
│   ├── README.md             dev e build do front
│   ├── package.json          dependências npm; package-lock.json trava versões
│   ├── vite.config.ts        proxy de /api, /auth e /users para a API em dev
│   ├── components.json       config do registry shadcn
│   ├── index.html            entrada da SPA
│   ├── public/               estáticos servidos como estão
│   └── src/                  código do front (lista abaixo)
│
├── docs/                     documentação estável
│   ├── adr/                  22 ADRs: toda decisão de arquitetura, uma por arquivo
│   ├── MOTIVACOES.md         por que cada escolha e qual alternativa caiu
│   ├── ESTRUTURA.md          este arquivo
│   ├── WORKFLOW.md           regras do trabalho autônomo com agentes
│   ├── AGENT-PROMPT.md       prompt-padrão que todo agente executor segue
│   ├── ENTREVISTA.md         guia de entrevista: perguntas prováveis por ADR e pelo workflow (ticket 19)
│   ├── DECISOES-AUTONOMAS.md decisões que agentes tomaram sem ADR: ticket, decisão, alternativa, porquê
│   ├── LACUNAS.md            onde o código diverge do ADR ou ficou aresta
│   ├── UI-GUIA.md            regras de tela e verificação visual por screenshot
│   ├── INFRA.md              runbook do VPS, do deploy e do CI
│   ├── MCP-RECOMENDADOS.md   servidores MCP sugeridos para cadastrar
│   ├── UX-AUDITORIA.md       auditoria de UX das telas
│   └── WIZARD-GOOGLE.md      passo a passo do projeto OAuth no Google (parte humana do ticket 18)
│
├── .scratch/desafio/         estado vivo do trabalho com IA (planejamento e execução)
│   ├── map.md                destino, marco, decisões até agora, névoa, fora de escopo
│   ├── issues/               tickets NN-slug.md: contexto, o que construir, aceite, Blocked by, Answer
│   ├── LEDGER.md             uma linha por execução de ticket: início, fim, resultado, commit
│   ├── HANDOFF.md            estado do orquestrador para a próxima sessão retomar
│   ├── MANHA.md              pendências que só o Toneli resolve
│   └── screens/              screenshots de verificação visual, prefixo = ticket
│
├── research/                 pesquisa feita antes dos ADRs, com fontes
│   ├── 01-frameworks-e-reuso.md      frameworks de agente, apps prontos, libs de busca e scraping
│   ├── 02-modelos-gemini-jev.md      modelos, preços e o Jev
│   ├── 03-mcp-conectores-deploy.md   MCP, conector Google, auth, deploy, observabilidade
│   └── 04-workflow-autonomo-dev.md   como rodar Claude Code sem supervisão
│
├── spike/                    ticket 01: provas descartáveis dos riscos de integração
│   ├── RESULTADO.md          9 hipóteses, veredito e custo de cada
│   ├── py/                   scripts h2..h7 (stream, usage, cache, MCP)
│   ├── web/                  AI Elements em Vite
│   └── docker-compose.yml    Postgres do spike
│
├── deploy/                  produção (ADR 0014): `docker-compose.yml` (app, migrate, postgres), `deploy.sh`, `backup.sh`, `cron-tess-chat`, `nginx-tess-chat.conf`; `mcp-demo/` é o servidor MCP de demo (ticket 17)
├── .github/workflows/        `deploy.yml`: testes e build em push e PR, deploy por ssh em push na main
├── docker/postgres-init/     01-roles.sql: cria o papel tess_app (runtime, sem DDL)
├── scripts/                  wizard-google.sh: wizard interativo do OAuth Google
├── data/                     fora do git. attachments/ = arquivos de Anexo em dev; manual09/ = entradas do teste manual do ticket 09 (INFERIDO pelo nome)
└── .playwright-mcp/          fora do git. Saída local do Playwright MCP
```

### `api/app/`: um módulo por conceito

Cada módulo junta, no mesmo arquivo, o modelo SQLAlchemy, as regras e o `APIRouter`. Detalhe em `MOTIVACOES.md`, seção Arquitetura.

| Módulo | Papel |
|---|---|
| `main.py` | monta o app: registra os routers, lifespan (conta demo), SPA na última linha |
| `config.py` | lê o `.env` (classe `Settings` do pydantic-settings) |
| `db.py` | engine e sessão async, conecta como `tess_app` |
| `auth.py` | FastAPI-Users: cadastro, login JWT, conta demo, `login_failed` |
| `conversas.py` | Conversas, Mensagens, Anexos (tabelas e CRUD); dono só vê o que é dele |
| `chat.py` | o turno: histórico do banco, Compactação, reserva, Roteador, Tools, stream, persistência. Rotas `/stream` (retomada) e `/parar` (ticket 55) |
| `turnos.py` | turno em background: registro por Conversa (409), buffer SSE com replay e tail, `CancellationToken` do Parar. ADR 0023 |
| `credito.py` | Tabela de Preço, Ledger, Cap, reserva e acerto, painéis de Crédito |
| `tools.py` | registro de Tools, toggle por Conversa, `web_search` e `web_fetch`, wrapper de auditoria. Monta o toolset do turno com as Tools do Google (só com Conector) e as MCP do dono |
| `mcp.py` | Servidor MCP por Usuário: tabela `mcp_servers`, cadastro que conecta antes de gravar, barreira de SSRF, sonda antes do turno. Tickets 17 e 23 |
| `conectores.py` | Conector Google: tabela `connectors`, OAuth com `state` JWT e PKCE, tokens cifrados, refresh, Tools `gmail_search`, `gmail_read`, `gmail_send` (Rascunho, ADR 0013), `drive_search_read`. Ticket 18 |
| `google_transporte.py` | pontes das libs de auth do Google para o transporte httpx injetável (ADR 0017) |
| `mcp_oauth.py` | Servidor MCP por OAuth: descoberta, DCR, PKCE, troca de code e refresh. Ticket 52, ADR 0022 |
| `limpeza_anexos.py` | varredura diária de arquivos de Anexo órfãos, rodada pelo cron do VPS. Ticket 50 |
| `roteador.py` | Roteador com Jev e gate de confiança |
| `compactacao.py` | Compactação por Resumo, tabela `summaries` |
| `resiliencia.py` | retry com backoff, fallback de modelo, métricas do turno |
| `anexos.py` | upload e download de Anexo, entrega ao modelo |
| `shares.py` | Compartilhamento por corte, rota pública |
| `audit.py` | **escrita** de Evento de auditoria (tabela e função `audit()`) |
| `auditoria.py` | **leitura** da auditoria e visão de admin |
| `configuracao.py` | Configuração por Usuário e por Conversa. Ticket 14 |
| `estaticos.py` | serve `web/dist` com fallback de SPA |

### `web/src/`

| Pasta | Papel |
|---|---|
| `pages/` | uma tela por rota: Chat, Login, Configuração (`/config`), Tools, MCP (`/mcp`), Conectores (`/conectores`), Créditos, Auditoria, Admin, Compartilhados, Compartilhamento (link público), Placeholder (Perfil e 404) |
| `components/` | componentes nossos: `BlocoTool`, `SeletorTools`, `SeletorModelo`, `Anexos`, `MarcadorCompactacao`, `IndicadorContexto` (rosca até a Compactação), `Trabalhando` (indicador do turno), `RascunhoEmail`, `ItemCompartilhar`, `ModalLink`, `Logo`, `estados` (vazio, carregando, erro) |
| `components/ui/` | código do registry shadcn, copiado e não escrito à mão |
| `components/ai-elements/` | código do registry AI Elements, copiado. Ajuste nosso: `message.tsx` usa o `ModalLink` na confirmação de link externo |
| `layout/` | `AppLayout`: barra lateral e casca das telas logadas |
| `lib/` | cliente da API (`api.ts`, token Bearer) e helpers por tela (`mcp.ts`, `conectores.ts`, `tools.ts`...) |
| `hooks/` | `use-mobile.ts`, do registry shadcn |
| `tema.ts` | tema dark padrão com toggle |

### Tickets depois do 14

| Ticket | O que tocou | Status |
|---|---|---|
| 15 | painéis de Crédito e auditoria, admin | resolvido |
| 16 | deploy no VPS com CI, `deploy/`, `.github/workflows/deploy.yml` | resolvido: no ar em https://chat.toneli.dev.br |
| 17 | `mcp.py`, migração 0013, `pages/Mcp.tsx`, `deploy/mcp-demo/` | resolvido |
| 18 | `conectores.py`, migração 0012, `pages/Conectores.tsx` | resolvido |
| 19 | `README.md`, `docs/ENTREVISTA.md`, `.env.example` | resolvido (vídeo pendente no `MANHA.md`) |
| 20 | este arquivo e `MOTIVACOES.md` | resolvido |
| 21 | suíte completa em lote: `test_roteador.py`, `pages/Tools.tsx` | resolvido |
| 22 | `WORKFLOW.md` e `map.md` contam a prática | resolvido |
| 23 | Servidor MCP caído sai do turno; SSRF no cadastro. `mcp.py`, `chat.py`, `tools.py` | resolvido |
| 24 | este arquivo e `MOTIVACOES.md` com 17, 18, 21, 23 | resolvido |

Tickets 25 a 54: uma linha por execução em `.scratch/desafio/LEDGER.md`.

### `api/migrations/versions/`

| Migração | Ticket | O que cria |
|---|---|---|
| 0001 | 03 | `audit_events`, com REVOKE UPDATE, DELETE para `tess_app` |
| 0002 | 04 | `users` |
| 0003 | 05 | `conversations`, `messages`, `attachments` |
| 0004 | 06 | colunas de thinking e cache em `messages` |
| 0005 | 08 | Tabela de Preço, Ledger, Cap, com REVOKE no Ledger e no preço |
| 0006 | 10 | `tools` e toggle por Conversa |
| 0007 | 13 | `shares` |
| 0008 | 07b | `ativa_global` nas Tools |
| 0009 | 12 | `summaries` (Resumo) |
| 0010 | 06b | preço do `gemini-3.7-flash` (fallback) |
| 0011 | 14 | tabela `settings` |
| 0012 | 18 | `connectors` (tokens cifrados); `tools.origem` aceita `google`; semeia as 3 Tools do Google |
| 0013 | 17 | `mcp_servers` (header cifrado); `tools.mcp_server_id` com FK em cascata; `tess_app` ganha INSERT e DELETE em `tools`, limitados por RLS a `origem = 'mcp'` |
| 0014 | 25 | `email_drafts` (Rascunho de e-mail) e a Tool `gmail_send` (ADR 0013) |
| 0015 | 25 | `gmail_send` nasce ligada por Conversa |
| 0016 | 28 | descrição da Tool para o Usuário, separada da que o modelo recebe |
| 0017 | 29 | conta Google vinculada e Gmail disponível no Conector |
| 0018 | 30 | teto de tool calls na Configuração |
| 0019 | 42 | descrição de `drive_search_read` com PDF e recentes volta ao banco |
| 0020 | 52 | credencial OAuth cifrada e estado da conexão em `mcp_servers` (ADR 0022) |

## Onde mora cada conceito do `CONTEXT.md`

| Conceito | Backend | Tabela | Front | ADR |
|---|---|---|---|---|
| Usuário | `auth.py` | `users` | `pages/Login.tsx` | 0002 (auth no Python) |
| Conversa | `conversas.py` | `conversations` | `layout/AppLayout.tsx`, `pages/Chat.tsx` | — |
| Mensagem | `conversas.py` (tabela), `chat.py` (pergunta no início, resposta no fim do turno) | `messages` | `pages/Chat.tsx` | 0001 |
| Anexo | `anexos.py`, tabela em `conversas.py` | `attachments` + arquivo em `data/` | `components/Anexos.tsx` | — |
| Tool | `tools.py` (origem `nativa`, `google` ou `mcp`) | `tools`, `conversation_tools` | `pages/Tools.tsx`, `components/SeletorTools.tsx`, `components/BlocoTool.tsx` | 0009 |
| Servidor MCP | `mcp.py`; toolset montado em `tools.py`, sonda em `chat.py` | `mcp_servers`, `tools` com `origem = 'mcp'` | `pages/Mcp.tsx`, `components/SeletorTools.tsx` | 0009 |
| Conector | `conectores.py`. Setup do OAuth: `scripts/wizard-google.sh` e `docs/WIZARD-GOOGLE.md` | `connectors`, `tools` com `origem = 'google'` | `pages/Conectores.tsx` | 0010 |
| Roteador | `roteador.py`, chamado em `chat.py` | eventos `router_decision` em `audit_events` | linha "roteado para X" no Chat | 0005 |
| Compactação | `compactacao.py`, chamado em `chat.py` | `summaries` | `components/MarcadorCompactacao.tsx` | 0006 |
| Resumo | `compactacao.py` | `summaries` | idem | 0006 |
| Crédito | `credito.py` | soma de `credit_ledger` | `pages/Creditos.tsx` | 0004 |
| Tabela de Preço | `credito.py` | `price_table` (com vigência, somente-inserção) | — | 0003, 0004 |
| Ledger | `credito.py` | `credit_ledger` (somente-inserção) | `pages/Creditos.tsx` | 0004 |
| Cap | `credito.py` | `caps` (+ default no `.env`) | aviso de cap no Chat | 0004 |
| Compartilhamento | `shares.py` | `shares` | `pages/Compartilhamento.tsx`, `pages/Compartilhados.tsx` | 0008 |
| Evento de auditoria | `audit.py` (escrita), `auditoria.py` (leitura) | `audit_events` (somente-inserção) | `pages/Auditoria.tsx` | 0007, 0012 |
| Configuração | `configuracao.py` | `settings` (migração 0011) | `pages/Configuracao.tsx` | 0006 |

Nomes de tabela conferidos no `__tablename__` de cada módulo.

## Mapa de `REVISAR(human)`

Funções que o agente implementou no lugar do Toneli. São as que mais caem em entrevista. Busque com `grep -rn "REVISAR(human)" api/`.

| Módulo | Marcas | O que decidem |
|---|---|---|
| `credito.py` | 3 | custo real em micro-USD, tamanho da reserva, dia do gasto no fuso do browser |
| `compactacao.py` | 3 | gatilho pelo limiar, ponto de corte no início de turno, roda só no passo 1 |
| `chat.py` | 4 | estimativa local do input, gravar a resposta no fim, 502 só antes do primeiro evento, `rodar_turno` fora da request |
| `turnos.py` | 1 | leitor do buffer: replay desde o chunk 0 e tail |
| `roteador.py` | 1 | gate: força a Tool só com confiança acima do limiar |
| `resiliencia.py` | 1 | o que é erro transitório |
| `tools.py` | 2 | fallback Jina para trafilatura, Tool ativa = global E Conversa |
| `shares.py` | 2 | 404 único, corte no maior id |
| `conversas.py` | 2 | 404 para Conversa alheia, remoção física |
| `anexos.py` | 2 | tipo pelos bytes, só anexo próprio vai ao modelo |
| `auth.py` | 2 | `login_failed` por override, seed da conta demo |
| `auditoria.py` | 1 | quem vê o quê |
| `configuracao.py` | 1 | herança campo a campo |
| `mcp.py` | 3 | nome da Tool com o id do servidor, barreira de SSRF, conectar antes de gravar |
| `conectores.py` | 3 | refresh do token, primeiro arquivo legível do Drive, `state` do OAuth em JWT |

## Sugestões

Achados da revisão da estrutura (ticket 20). Nada foi movido: todo item quebraria referência em doc ou import. Os itens 1, 2 e 8 foram resolvidos depois; o item 4 em parte.

1. **`docs/WORKFLOW.md` descreve o plano, não o que rodou.** Ele fala de loop externo `claude -p` com teste como gate fora do Claude. O `HANDOFF.md` e o `LEDGER.md` mostram outra coisa: um orquestrador numa sessão do Claude Code disparando agentes em paralelo, e o próprio agente rodando os testes. Atualizar o WORKFLOW para contar a evolução. Detalhe em `MOTIVACOES.md`, seção Workflow. **Resolvido no ticket 22.**
2. **`map.md` está defasado.** Ainda diz que o agente grava `BLOCKED` e para, e que três funções são HITL. Desde 23/09 o agente decide o simples, registra em `DECISOES-AUTONOMAS.md` e marca `REVISAR(human)`. A seção "Not yet specified" também já foi resolvida em parte. **Resolvido no ticket 22.**
3. **`.scratch/` é o coração do fluxo de IA, mas o nome diz "descartável"** e a pasta começa com ponto (some em `ls` e em alguns navegadores de arquivo). Renomear quebra CLAUDE.md, WORKFLOW, AGENT-PROMPT, HANDOFF e tickets. Alternativa barata: o README do ticket 19 aponta para ela logo no topo.
4. **Referências a coisas que não existem:** `spike/out/` (citado como evidência em `spike/RESULTADO.md`), `deploy/` e `docs/INFRA.md` (citados no `AGENT-PROMPT.md`), `.github/` e Caddyfile (ADR 0011). Os quatro últimos são do ticket 16. `spike/out/` precisa de correção no RESULTADO ou do commit da evidência. **Em parte:** `deploy/`, `docs/INFRA.md` e `.github/` existem desde o ticket 16. O Caddy saiu (ADR 0014). Falta `spike/out/`.
5. **`LEDGER.md` não tem a coluna de turnos** que o `WORKFLOW.md` pede.
6. **Pares de nome parecidos:** `audit.py` (escrita) e `auditoria.py` (leitura); `config.py` (`.env`) e `configuracao.py` (Configuração do domínio, tabela `settings`). A classe `Settings` de `config.py` e a tabela `settings` do ticket 14 são coisas diferentes com o mesmo nome. Não renomear agora (imports); explicar no README.
7. **Nome do ADR 0011 cita DuckDNS**, mas a decisão final é o domínio próprio. O texto do ADR já explica; renomear o arquivo quebra o link no `map.md`.
8. **Sem README na raiz.** O avaliador cai direto na lista de arquivos. É o ticket 19. **Resolvido no ticket 19.**
