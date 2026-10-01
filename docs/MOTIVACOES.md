# Motivações

Por que cada escolha, e qual alternativa caiu. Onde um ADR já decide, este doc resume em 2 linhas e linka. O que não tem fonte no código, nos ADRs ou em `research/` vai marcado **INFERIDO**.

Onde o código diverge de um ADR, a divergência está em `docs/LACUNAS.md`. Este doc não repete.

Mapa de pastas e de conceitos: `docs/ESTRUTURA.md`.

## 1. Stack

| Escolha | Por quê | Alternativa descartada | Fonte |
|---|---|---|---|
| **Python** | Python é a escolha defendida. A lógica avaliada está no backend. | TypeScript com o template Vercel Chatbot. | [ADR 0001](adr/0001-backend-python-pydantic-ai.md), `research/01` §3 |
| **Python 3.14** | Versão mais nova estável no momento. | 3.12 ou 3.13. | **INFERIDO**. Nenhum doc registra o motivo. |
| **uv** | Um lock (`uv.lock`), `uv sync --frozen` no Dockerfile, instala rápido. | pip + requirements, Poetry. | **INFERIDO**. Nenhum doc registra o motivo; o uso está no `Dockerfile` e no `AGENT-PROMPT.md`. |
| **FastAPI** | Async, casa com o streaming e com o FastAPI-Users para auth. Dependências (`Depends`) servem de ponto de troca nos testes. | — | [ADR 0001](adr/0001-backend-python-pydantic-ai.md), [ADR 0002](adr/0002-front-vite-servido-pelo-fastapi.md) |
| **Pydantic AI** | Traz de fábrica: troca de provedor, tool calling tipado, cliente MCP, `RunUsage`, hook de histórico para a Compactação, adapter do protocolo do AI SDK. Framework fino: cada peça é explicável. | LangGraph (API larga, menos tipada). Fork do LibreChat (Node + Mongo, soa "instalou app pronto"). | [ADR 0001](adr/0001-backend-python-pydantic-ai.md) |
| **Postgres** | `jsonb` para o payload da auditoria. Papéis e `REVOKE` por tabela: o papel `tess_app` não pode fazer UPDATE nem DELETE em `audit_events`, `credit_ledger` e `price_table`. Isso torna "somente-inserção" uma garantia do banco, não do código. | SQLite: não tem papéis nem `REVOKE`. | [ADR 0007](adr/0007-auditoria-append-only.md), `docker/postgres-init/01-roles.sql`, migrações 0001 e 0005. SQLite como alternativa: **INFERIDO**. |
| **Alembic** | Migração versionada; cada migração também dá os `GRANT`/`REVOKE` da tabela que cria. Dois papéis: `tess_owner` migra, `tess_app` roda. | `create_all` do SQLAlchemy no startup. | Uso: `01-roles.sql` ("permissões por tabela vêm das migrações"). Alternativa: **INFERIDO**. |
| **React + Vite + shadcn + AI Elements** | Front é detalhe na vaga. Vite buildado é servido pelo FastAPI: um container, um deploy. `useChat` fala o protocolo que o adapter do Pydantic AI emite. | Next.js em container separado. shadcn puro com parser de stream manual. | [ADR 0002](adr/0002-front-vite-servido-pelo-fastapi.md) |
| **Gemini (`gemini-3.8-flash`, tier pago)** | 1M de contexto, tool calling paralelo, PDF e imagem nativos, thinking configurável, barato. Free tier usa o conteúdo para treino. Resumo usa `gemini-3.1-flash-lite`. | Gemini Pro (~3x o preço sem ganho visível). Free tier. | [ADR 0003](adr/0003-modelo-gemini-flash-pago.md) |
| **Tavily** (`web_search`) | Tool nossa, passa pelo registro, tem toggle e Evento de auditoria. Free tier de 1.000 créditos/mês sem cartão. | Busca embutida do Gemini (fora do registro, sem toggle nem evento). Serper, Exa, Brave (Brave pede cartão). | [ADR 0009](adr/0009-registro-unico-de-tools-e-mcp-client.md), `research/01` §4.2. Tavily sobre Serper: **INFERIDO**. |
| **Jina Reader + trafilatura** (`web_fetch`) | Jina devolve a página já limpa para LLM. Se falhar, GET direto + trafilatura, lib local e leve. Texto cortado em 20.000 caracteres. | URL context do Gemini (fora do registro). Crawl4AI (exige Chromium no VPS). Firecrawl (cota por página). | [ADR 0009](adr/0009-registro-unico-de-tools-e-mcp-client.md), `research/01` §4.1, `app/tools.py` |
| **Jev (TypeSafe)** | Roteador barato (US$ 0,042 por 1M) e rápido (70 a 500 ms) que devolve escolha tipada com probabilidade. Forçar a Tool com confiança alta deixa o Gemini previsível. | Deixar só o Gemini escolher (`AUTO`) em todo turno. | [ADR 0005](adr/0005-jev-como-roteador-pre-chamada.md) |

## 2. Estilo arquitetural

**Nome preciso: monólito modular, fatiado por conceito do domínio.** Não é arquitetura em camadas. Não é hexagonal.

**O que é:**
- **Monólito:** um processo, um deploy, um banco. A API FastAPI também serve o front buildado ([ADR 0002](adr/0002-front-vite-servido-pelo-fastapi.md)).
- **Modular por conceito:** cada arquivo de `api/app/` corresponde a um termo do `CONTEXT.md` (`credito.py`, `roteador.py`, `compactacao.py`, `shares.py`...). Cada um tem seu `APIRouter`, e `main.py` só registra os routers. O front espelha isso: uma tela por conceito em `web/src/pages/`.
- **Orquestração num ponto só:** `chat.py` compõe o turno chamando os módulos na ordem: histórico do banco, Compactação, reserva de Crédito, Tools da Conversa, Roteador, Anexos, modelo com retry e fallback, persistência e acerto.

**O que não é:**
- **Não é camadas** (controller, service, repository em pastas separadas). Dentro de um módulo convivem o modelo SQLAlchemy, as regras e a rota HTTP.
- **Não é hexagonal.** Não há portas nem adaptadores formais. Tipos do Pydantic AI aparecem nas regras do domínio: `debit()` em `credito.py` recebe `RunUsage` direto.

**Onde fica a fronteira entre API, domínio e infra:**
- **API (HTTP):** funções decoradas no `APIRouter` de cada módulo. Validam entrada, resolvem Usuário e sessão por `Depends`.
- **Domínio:** funções puras, sem I/O, dentro do mesmo módulo. Exemplos: `debit()` (custo em micro-USD), `apply_gate()` (gate do Roteador), `should_compact()` e `ponto_de_corte()` (Compactação), `transitorio()` (retry).
- **Infra:** `db.py` (engine e sessão), `config.py` (`.env`), e os clientes externos injetados por `Depends`: `modelo()`, `modelo_reserva()`, `modelo_resumo()`, `transporte()` (HTTP das Tools), `cliente_jev()`. Os testes trocam essas dependências por `FunctionModel` ou `httpx.MockTransport` com resposta gravada.

**Por que este estilo:** prazo de ~2 dias e um dev que precisa defender cada peça ([ADR 0001](adr/0001-backend-python-pydantic-ai.md)). Um arquivo por conceito deixa "onde mora X" com uma resposta só. Camadas triplicariam o número de arquivos sem segundo consumidor que justifique a abstração. **INFERIDO**: o raciocínio sobre camadas não está escrito em nenhum ADR; a estrutura é a observada no código.

**Custo conhecido:** `chat.py` concentra o fluxo. Dois agentes não podem editá-lo ao mesmo tempo (`HANDOFF.md`, "gargalo").

## 3. Padrões

| Padrão | Resumo | Onde |
|---|---|---|
| **Registro único de Tools** | Toda Tool, nativa ou MCP, passa por um registro: ativável por Conversa e auditada por chamada. A auditoria é um wrapper (`Auditada`) em volta do toolset, então cada Tool nova é auditada sem código extra. As Tools do Google (18) e as MCP (17) entram no mesmo registro e no mesmo wrapper. | [ADR 0009](adr/0009-registro-unico-de-tools-e-mcp-client.md), `app/tools.py` |
| **Ledger de Crédito** | Micro-USD inteiro, calculado do uso real do provedor vezes a Tabela de Preço vigente. Reserva antes da chamada, acerto depois. Saldo é a soma do Ledger. | [ADR 0004](adr/0004-credito-em-micro-dolar-do-uso-real.md), `app/credito.py`. Reserva estimada localmente: ver `LACUNAS.md`. |
| **Roteador com gate** | Jev decide a Tool antes do Gemini. Confiança no limiar ou acima força a Tool; abaixo, o Gemini decide. O Roteador escolhe Tool, nunca permissão. | [ADR 0005](adr/0005-jev-como-roteador-pre-chamada.md), `app/roteador.py` |
| **Compactação por Resumo** | Acima do limiar da Configuração, turnos antigos viram Resumo do flash-lite dentro do mesmo turno. Originais continuam no banco. Par tool-call e resultado nunca é separado. | [ADR 0006](adr/0006-compactacao-por-resumo-com-limiar-configuravel.md), `app/compactacao.py`. Gatilho lê a última chamada do turno anterior, não a soma: [ADR 0025](adr/0025-gatilho-le-ultima-chamada.md). |
| **Auditoria por evento** | Tabela `audit_events` somente-inserção, garantida por `REVOKE`. Ledger e auditoria são tabelas distintas: uma é dinheiro, a outra é história. A tela de auditoria é o painel de observabilidade do agente. | [ADR 0007](adr/0007-auditoria-append-only.md), [ADR 0012](adr/0012-resiliencia-retry-e-fallback-de-modelo.md), `app/audit.py` |
| **Retry e fallback de modelo** | Até 3 tentativas com backoff em erro transitório. Depois troca de modelo. O modelo que respondeu vai para a Mensagem e o Ledger. Retry é um wrapper (`ComRetry`) em volta de cada modelo da cadeia. | [ADR 0012](adr/0012-resiliencia-retry-e-fallback-de-modelo.md), `app/resiliencia.py` |
| **Compartilhamento por corte** | Link guarda o id da última Mensagem; a leitura filtra até ele. Sem cópia. Revogado e inexistente dão o mesmo 404. | [ADR 0008](adr/0008-compartilhamento-por-corte.md), `app/shares.py` |
| **Histórico só do banco** | Do body do `useChat` o servidor usa só a última mensagem. O resto vem do Postgres. | `DECISOES-AUTONOMAS.md` (06). Motivo: o front pode mandar histórico adulterado. |

**Wrapper como padrão repetido:** auditoria de Tool (`Auditada`) e retry de modelo (`ComRetry`) usam o mesmo formato: embrulhar o objeto do Pydantic AI em vez de mexer em cada Tool ou em cada chamada. Uma regra transversal fica num ponto só.

## 4. Infraestrutura

**Escolha:** VPS compartilhado (aarch64), Docker Compose com `app` e `postgres` (`deploy/docker-compose.yml`), atrás do nginx do host com certbot, domínio próprio `chat.toneli.dev.br`. Resumo do [ADR 0014](adr/0014-deploy-nginx-do-host-no-vps-compartilhado.md), que substituiu a parte Caddy e OCI do [ADR 0011](adr/0011-deploy-compose-caddy-duckdns-oci.md). A conta OCI nova falhou; um Caddy nosso brigaria pelas portas 80/443 do nginx que já serve outra produção.

**Descartados no ADR 0011:**
- Cloudflare Quick Tunnel: não passa SSE, mata o streaming.
- ngrok: URL efêmera e tela intermediária.
- Coolify e Dokploy: 2 GB de RAM e horas de setup.
- DuckDNS: era o plano sem domínio; o domínio chegou em 23/09.

**Por que não serverless:** **INFERIDO**. Nenhum doc compara. Argumentos a partir do código:
- O chat é stream longo (SSE) com várias chamadas ao modelo por turno. Função serverless tem timeout e cobra por duração.
- Os Anexos ficam no disco do servidor, com metadados no Postgres (`map.md`, grilling 23/09). Serverless não tem disco persistente.
- Um container já serve front e API ([ADR 0002](adr/0002-front-vite-servido-pelo-fastapi.md)). Separar em funções volta a dobrar a superfície a defender.

**Por que não Kubernetes:** **INFERIDO**. Um app, um banco, um público pequeno, uma semana no ar. Compose descreve os três serviços num arquivo. K8s traz control plane, ingress e manifests sem nenhum requisito que peça escala ou alta disponibilidade.

**Estado:** no ar em https://chat.toneli.dev.br (ticket 16). `deploy/` tem o compose de produção, `deploy.sh`, backup diário por cron e o site nginx. O CI (`.github/workflows/deploy.yml`) roda testes e build em push e PR e faz o deploy por ssh em push na `main`. Runbook em [`INFRA.md`](INFRA.md).

## 5. Fluxo de trabalho com IA

**Resumo:** o Toneli decide (ADRs, glossário, tickets). Agentes executam um ticket cada. Toda decisão tomada sem ele fica registrada para ele estudar depois.

### As peças

| Peça | Papel | Onde |
|---|---|---|
| **Pesquisa** | Levantamento com fontes antes de decidir. Cada ADR cita a sua. | `research/01..04` |
| **Spike** | Queimar os riscos de integração antes do código real: 9 hipóteses, todas passaram. Ajustes propagados aos tickets. | `spike/RESULTADO.md`, ticket 01 |
| **ADRs** | Toda decisão de arquitetura, com opções e porquê. Agente não contraria ADR sem escrever outro. | `docs/adr/` |
| **Glossário** | Um termo por conceito, usado no código, nos tickets e na conversa. | `CONTEXT.md` |
| **Tickets** | Fatia vertical com contexto, o que construir, aceite testável e `Blocked by`. Fecham com `## Answer`. | `.scratch/desafio/issues/` |
| **Mapa** | Destino, marco, decisões, o que ainda é névoa, fora de escopo. | `.scratch/desafio/map.md` |
| **Prompt-padrão** | O mesmo roteiro para todo agente executor: o que ler, TDD, como commitar sem engolir arquivo alheio. | `docs/AGENT-PROMPT.md` |
| **Orquestrador + executores** | Uma sessão do Claude Code escolhe o próximo ticket livre e dispara um agente Opus por ticket, às vezes em paralelo. Confere o commit, dá push, encerra o agente. | `.scratch/desafio/HANDOFF.md` |
| **LEDGER** | Uma linha por execução: início, fim, resultado com contagem de testes e de chamadas reais, commit. | `.scratch/desafio/LEDGER.md` |
| **DECISOES-AUTONOMAS** | Decisão fora de ADR: o agente escolhe a opção mais simples que atende o aceite e registra ticket, decisão, alternativa e porquê. Não para. | `docs/DECISOES-AUTONOMAS.md` |
| **LACUNAS** | Onde o código diverge do ADR ou ficou aresta. Vira "limites conhecidos" no README. | `docs/LACUNAS.md` |
| **Golden set** | Casos com resposta conhecida, gravados uma vez e reusados sem custo: 10 frases do Roteador, 9 certas, a 10ª ambígua cai abaixo do limiar. | `api/tests/fixtures/jev_golden.json`, ticket 11 |
| **Verificação visual** | Ticket de front fecha com screenshot no Brave, dark, 1440x900. A revisão visual é por screenshot. | `docs/UI-GUIA.md`, `.scratch/desafio/screens/` |

### Por que assim

- **Toneli precisa defender cada decisão** (`CLAUDE.md`). Por isso arquitetura só entra por ADR, e decisão de agente fica escrita com a alternativa descartada.
- **Nada bloqueia a noite.** No plano original, três funções eram escritas pelo Toneli e o agente parava em `BLOCKED` diante de decisão nova (`map.md`). Troca: velocidade agora, estudo depois.
- **Custo contado.** Chamadas reais a Gemini, Tavily e Jev têm teto por ticket e aparecem no LEDGER. Testes usam resposta gravada ou modelo de teste. Suíte completa e golden set rodam em lote no fim do bloco.
- **Teste como prova.** TDD por ticket, testes de integração contra o Postgres real, e teste de mutação nas regras críticas (o LEDGER registra "mutação pega").

### Plano versus prática

- **Plano** (`research/04`, `WORKFLOW.md`): loop externo em script chamando `claude -p` um ticket por vez, com a suíte de testes como gate fora do Claude.
- **Prática** (`HANDOFF.md`, `LEDGER.md`): uma sessão orquestradora do Claude Code disparando agentes executores em paralelo no mesmo working tree. O agente roda os testes do próprio ticket; o orquestrador confere e faz push.
- **Por que mudou:** **INFERIDO**. Nenhum doc registra. Hipótese: paralelismo entre tickets independentes e o orquestrador conseguindo corrigir rumo entre tickets.
- **Custo da prática:** stage compartilhado. Um commit engoliu arquivos de outro ticket (`2c738a6`). Regra nova: commit só com `git commit --only` dos próprios arquivos, e `chat.py` com um agente por vez.
- `WORKFLOW.md` e `map.md` passaram a contar a prática no ticket 22.

## 6. MCP e Conectores (tickets 17, 18 e 23)

Decisões que os agentes tomaram sem ADR. Os ADRs [0009](adr/0009-registro-unico-de-tools-e-mcp-client.md) e [0010](adr/0010-conector-google-oauth-direto.md) continuam valendo. A linha completa, com a alternativa descartada, está em `DECISOES-AUTONOMAS.md`, no ticket indicado.

### Conector Google (ticket 18)

| Decisão | Por quê | Fonte |
|---|---|---|
| **Auth pelas libs oficiais (`google-auth`, `google-auth-oauthlib`) com PKCE; Gmail e Drive em `httpx`** | O `Flow` e o `Credentials` dão troca de code, refresh e PKCE prontos e mantidos pelo Google. O `google-api-python-client` caiu: maintenance mode, sobre httplib2 deprecated, síncrono. Não existe cliente oficial async para Gmail e Drive. Duas pontes (`app/google_transporte.py`) passam as libs pelo mesmo `httpx.MockTransport` dos testes. | [ADR 0017](adr/0017-auth-google-com-libs-oficiais-e-pkce.md) |
| **Tokens cifrados com Fernet**, chave `CONNECTORS_KEY` no `.env` | Token do Google em claro no banco vaza com um dump. Fernet é padrão e a chave fica fora do banco. Custo: trocar a chave obriga o usuário a reconectar. | idem |
| **Origem `google` no registro de Tools** | O filtro "só aparece com Conector" sai de uma coluna, sem lista de nomes no código. O glossário ainda diz só `nativa` ou `mcp`. | idem, migração 0012 |
| **Filtro de Conector em `estado_da_conversa`** | Um ponto só cobre o toolset do turno, a lista de Tools da Conversa e as opções do Roteador. Zero edição em `chat.py`. | idem |
| **`state` do OAuth é JWT assinado** (Usuário, 10 min) | O callback chega por GET do browser, sem o Bearer do front. O JWT identifica o dono e barra CSRF sem tabela de states. | `conectores.py` |
| **Redirect final para `{PUBLIC_BASE_URL}/conectores`** | Em produção API e front têm a mesma origem ([ADR 0002](adr/0002-front-vite-servido-pelo-fastapi.md)). Uma variável basta. | idem |
| **`drive_search_read` lê só o primeiro arquivo legível**; PDF do Drive fica fora | O aceite pede "resume o arquivo Y"; um Doc cobre a demo. PDF pediria extrator novo. | idem |
| **Refresh 60 s antes de vencer**; falha vira texto para o modelo | O modelo repassa "reconecte em Conectores" e o turno não quebra. Refresh e falha geram Evento de auditoria. | idem |

### Cliente MCP (ticket 17)

| Decisão | Por quê | Fonte |
|---|---|---|
| **Nome da Tool MCP = `<slug>_<4 hex do id>_<tool>`**, com `tools.mcp_server_id` | `tools.nome` é PK global. Dois Usuários com o mesmo servidor colidiriam. O hex do id resolve sem mexer na PK nem em `chat.py`. | `DECISOES-AUTONOMAS.md` (17) |
| **App grava em `tools` só com RLS `origem = 'mcp'`** | O cadastro precisa escrever no registro único (ADR 0009). A RLS deixa nativas e Google fora do alcance da app. | idem, migração 0013 |
| **Header de auth colado inteiro, cifrado com o Fernet do 18** | GitHub e o demo só pedem Bearer. Reusa a cifra que já existe. A API nunca devolve o header, só `tem_auth`. | idem |
| **Cadastro conecta e lista antes de gravar** | Erro legível no cadastro (502 com o motivo) em vez de servidor gravado e quebrado. | `mcp.py` |
| **Tools listadas só no cadastro**; no turno, o filtro deixa passar os nomes do registro | Toggle por Conversa precisa de linha no registro. Sincronizar a cada turno é YAGNI. Custo: Tool nova no servidor pede recadastro. | idem |
| **Toggle `ativo` por servidor** | Desligar sem apagar. A coluna já estava no ticket. | idem |
| **`GET /api/tools` esconde Tools MCP de outros Usuários** | O catálogo global vazaria nome e descrição de servidores alheios. | idem |
| **Servidor demo sem proteção de DNS rebinding** | No compose o Host é `mcp-demo`, e a proteção do SDK recusa esse Host. | idem |
| **Ressalvas do 17 (SSRF e servidor caído)** | Ficaram fora do aceite e viraram o ticket 23. | idem |

### Resiliência MCP e SSRF (ticket 23)

| Decisão | Por quê | Fonte |
|---|---|---|
| **Só `https://`, e todo IP resolvido precisa ser `is_global`** | `is_global` cobre privado, loopback, link-local (metadata da nuvem), reservado e CGNAT de uma vez. Checar todos os IPs impede o host com um IP público e um interno. | `DECISOES-AUTONOMAS.md` (23) |
| **Config `ENV` com default `dev`**; em `dev`, `http://` para o demo passa | Segue o padrão do `config.py` e não quebra os testes do 17. Produção precisa de `ENV=prod`. | idem, `.env.example` |
| **Sonda antes do turno** (conecta e lista, 3 s, em paralelo) | Servidor caído sai do turno com evento `mcp_server_unreachable`, em vez de derrubar a Conversa. Custo: um handshake a mais por servidor por turno. | idem |
| **Aviso no stream como parte de texto `aviso-mcp`** | Determinístico, sem chamada ao Gemini e sem mudança em `web/`. | idem |
| **Ressalva: checagem de SSRF só no cadastro** | DNS rebinding depois do cadastro não está coberto. Fixar o IP pediria transporte HTTP próprio no cliente MCP. | idem |

### Roteador e tools MCP (ticket 36)

| Decisão | Por quê | Fonte |
|---|---|---|
| **Roteador só força tool `nativa` ou `google`; tool `mcp` fica sugerida (`forcada=false`, `sugerida=true`) e o modelo escolhe livre** | O Jev não tem contexto para escolher entre tools genéricas de servidor externo (planner, busca de docs, feedback). Nos tickets 33 e 35 ele forçou `stripe_implementation_planner` (0,78 e 0,83) e o turno terminou sem ação. Forçar errado custa o turno inteiro. Alternativa descartada: tirar as tools MCP da entrada do Jev (perde o registro da decisão na Auditoria e na Tela do Roteador). | [ADR 0005](adr/0005-jev-como-roteador-pre-chamada.md) (emenda 23/09), `app/roteador.py` |

## 7. Turno em background (ticket 55)

| Decisão | Por quê | Fonte |
|---|---|---|
| **O turno roda numa `asyncio.Task` fora da request. A resposta HTTP só lê um buffer** | Trocar de tela ou dar F5 cancelava o run no `http.disconnect`. As tools MCP já tinham agido, e o turno sumia sem Mensagem e sem cobrança. | [ADR 0023](adr/0023-turno-em-background.md) |
| **Buffer em memória, sem Redis** | O deploy é um uvicorn só. Broker seria infra para um problema que ainda não existe. Com multi-worker, o buffer vai para Redis. | idem |
| **Pergunta gravada no início** | Ao voltar para a tela, a pergunta aparece na hora, e o `/stream` retoma a resposta. Custo: turno que falha deixa a pergunta sem resposta. | idem |
| **Parar pelo `CancellationToken`, não por `Task.cancel()`** | O token vira `RunCancelled`, e o `on_cancel` grava o parcial e cobra, pelo mesmo caminho do `ComTeto`. `Task.cancel()` vira `CancelledError` e perde o parcial. | idem |
| **Replay desde o chunk 0 no `/stream`** | O `useChat` com `resume: true` monta a resposta do zero. Sem o `start`, ele não tem o message id. | `TurnoAtivo.ler` |

## 8. Ligação: voz e tela (tickets 75 a 82)

| Decisão | Por quê | Fonte |
|---|---|---|
| **Proxy WebSocket no FastAPI, não token efêmero no browser** | O servidor precisa ver o `usage_metadata` do Gemini. Com token efêmero, Cap e auditoria dependeriam do que o browser reporta. Preço: um salto a mais, dezenas de ms (INFERIDO). Caíram SSE, WebRTC e a cascata STT → LLM → TTS. | [ADR 0026](adr/0026-ligacao-por-gemini-live-com-proxy-websocket.md), `ESTUDO-VOZ.md` parada 6 |
| **Ticket de uso único de 30 s, não JWT na URL** | O browser não manda header em WebSocket. A URL fica no log do nginx, e o JWT vale 24 h. O `pop` vem antes da checagem de validade. | ADR 0026, `voz.py` `_consumir` |
| **A Ligação ocupa a vaga de turno da Conversa** | Reusa o registro do turno em background: texto durante a Ligação dá 409, sem lock novo. | ADR 0026, [ADR 0023](adr/0023-turno-em-background.md) |
| **Relay de duas tasks e fim único no `finally`** | Cada sentido fala quando quer. Um caminho de fim só evita esquecer acerto ou vaga e deixar 409 eterno. | `voz.py` `_relay`, `_encerrar` |
| **Reserva de 9 min antes de abrir; acerto pelo uso real somado no fim; preço de tabela na chave free** | Cap só dispara se o custo não for zero. A reserva é US$ 0,345 (o spike mediu o Frame em 264 tokens, e o ADR contava mais barato). Divergência com o ADR em `LACUNAS.md`. | [ADR 0027](adr/0027-credito-da-ligacao.md), `DECISOES-AUTONOMAS.md` (76), `credito.py` `caber` |
| **Pensamento cobrado como saída de texto** | O `thoughts_token_count` fica fora do total e o ADR 0027 não tinha linha de preço. **INFERIDO.** O modelo base também pensa, não só o `-extended-thinking`. | `spike/live/RESULTADO.md`, migração 0024 |
| **Frame a 1 fps, JPEG 0,7, lado maior 1280** | A API aceita 1 imagem por segundo; o caso de uso é texto que muda pouco. 264 tokens a 1280 e a 768: a resolução não muda o custo. | [ADR 0028](adr/0028-captura-de-tela-1-fps.md), spike 75 |
| **Adendo de voz diz primeiro que a tela chega** | A frase "sem tela, diga que não vê nada", solta, fez o modelo negar a tela que tinha. Causa não isolada (INFERIDO). | `voz.py` `ADENDO_VOZ`, `DECISOES-AUTONOMAS.md` (75) |
| **Sem Jev e sem tools** | O Jev força a tool no passo 1 de um turno de requisição e resposta. A voz é fluxo contínuo. | ADR 0026 item 6 |
| **Histórico em texto na instrução; falas voltam como um par por troca com `data-ligacao`** | Compactação e corte contam turnos por Mensagem. Sem migração; o modelo de texto ignora `data-*`. | `DECISOES-AUTONOMAS.md` (77), `voz.py` `_trocas` |
| **Origem `ligacao` derivada da linha do Ledger** | Sem coluna nova nem migração. Custo: trocar o modelo Live na config reclassifica Ligações antigas como Compactação. | `DECISOES-AUTONOMAS.md` (82), `credito.py` `_origem` |
| **AudioWorklet e PCM16 no microfone; fila de `AudioBufferSourceNode` na saída** | O Live pede PCM cru; o `MediaRecorder` entrega Opus. A fila agendada evita picote, e esvaziá-la é o barge-in. | `ESTUDO-VOZ.md` paradas 2, 13 e 14 |
| **nginx: location própria para o WebSocket** | `Upgrade` e `Connection` são hop-by-hop. Mudar o `Connection ""` global afetaria o SSE. | `deploy/nginx-tess-chat.conf`, `INFRA.md` |
| **Smoke de produção com WAV e canvas** | Com dispositivo falso, o `getDisplayMedia` do Brave entrega um padrão verde. Canvas mantém trilha, 1 fps, JPEG e WebSocket reais. | `DECISOES-AUTONOMAS.md` (80) |
| **Limites assumidos: 9 min, sem session resumption, um processo** | Cada um custa código acima do ganho na demo (YAGNI). Restart derruba a Ligação. | ADR 0026 (Consequências), `ESTUDO-VOZ.md` parada 23 |
