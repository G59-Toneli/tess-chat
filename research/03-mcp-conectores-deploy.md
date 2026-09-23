# 03 — MCP, conectores Google, auth, deploy OCI, auditoria, compartilhamento

Pesquisa feita em 2026-09-22. Fonte primária por afirmação. Tudo que não foi confirmado em fonte está marcado **INFERIDO**.

---

## 1. MCP em 2026

### Fatos

- **Versão atual da spec: `2026-07-28`.** Fonte: https://modelcontextprotocol.io/specification/versioning
- É a maior revisão desde o lançamento. Ela remove sessões (`initialize`/`initialized` e `Mcp-Session-Id`). Cada request carrega versão, identidade e capabilities do cliente. Fonte: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- **Deprecados, com janela mínima de 12 meses:** Roots, Sampling, Logging, Dynamic Client Registration (trocado por Client ID Metadata Documents) e o transporte legado HTTP+SSE. Fonte: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- **Transportes:** stdio (processo local) e Streamable HTTP (remoto). Streamable HTTP agora exige headers `Mcp-Method` e `Mcp-Name` e `MCP-Protocol-Version`. Fonte: https://blog.modelcontextprotocol.io/posts/2026-07-28/ e https://modelcontextprotocol.io/specification/versioning
- **Compatibilidade entre eras (achado principal).** A spec define cliente/servidor "legacy" (`2025-11-25` e anteriores, com handshake) e "modern" (`2026-07-28`). Matriz oficial:
  - Cliente legacy → servidor modern-only: **falha** (HTTP 400, sem fallback).
  - Cliente modern → servidor legacy: **falha**.
  - Cliente dual-era → qualquer servidor: funciona.
  - Fonte: https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning

### SDKs oficiais

| SDK | Versão | Era | Fonte |
|---|---|---|---|
| Python `mcp` | 2.2.0 (linha estável v2) | v2 suporta `2026-07-28` "e toda revisão anterior" | https://pypi.org/pypi/mcp/json , https://github.com/modelcontextprotocol/python-sdk |
| Python `mcp` 1.x | 1.30.0 (2026-09-07), manutenção | só legacy | https://pypi.org/pypi/mcp/json , https://github.com/modelcontextprotocol/python-sdk/releases |
| TypeScript v2 | pacotes `@modelcontextprotocol/client` e `@modelcontextprotocol/server` | `2026-07-28` | https://github.com/modelcontextprotocol/typescript-sdk |
| TypeScript v1 | `@modelcontextprotocol/sdk` 1.30.0 | legacy; fixes por ≥6 meses | https://registry.npmjs.org/@modelcontextprotocol/sdk/latest , https://github.com/modelcontextprotocol/typescript-sdk |
| FastMCP | 4.0.5; tem cliente | era **INFERIDO** | https://pypi.org/pypi/fastmcp/json |

- Data de lançamento do `mcp` 2.2.0: **INFERIDO** (PyPI não retornou).
- Cliente do SDK Python v2 em Streamable HTTP: `async with Client("http://host/mcp") as client: await client.call_tool(...)`. "A URL means Streamable HTTP". Fonte: https://github.com/modelcontextprotocol/python-sdk

### Frameworks que viram cliente MCP em poucas linhas

| Framework | API atual | Era do cliente | Fonte |
|---|---|---|---|
| Pydantic AI (2.47.0) | `MCPToolset('url')` em `Agent(toolsets=[...])`; aceita `auth`, `headers`, `.prefixed()`. Doc não cita mais `MCPServerStreamableHTTP`. Por baixo usa FastMCP Client. Sem `list_tools()` documentado no toolset. | **INFERIDO** (doc cita specs 2025-06-18 e 2025-11-25) | https://pydantic.dev/docs/ai/mcp/client/ , https://pypi.org/pypi/pydantic-ai/json |
| LangChain `langchain-mcp-adapters` 0.3.2 | `MultiServerMCPClient`, transport `streamable_http` | **legacy-only**: exige `mcp<2.0.0,>=1.24.0` | https://pypi.org/pypi/langchain-mcp-adapters/json , https://github.com/langchain-ai/langchain-mcp-adapters |
| Vercel AI SDK | `createMCPClient` (não é mais `experimental_`), pacote `@ai-sdk/mcp`, transport `http` ou `sse`; `client.tools()` já converte para tools do AI SDK | **INFERIDO** (doc não cita versão da spec) | https://ai-sdk.dev/docs/reference/ai-sdk-core/create-mcp-client |
| google-genai (Python) | passa `ClientSession` do pacote `mcp` em `tools=[session]`; automatic function calling. **Experimental.** Só tools, sem resources/prompts. | depende da versão do `mcp` instalada; **INFERIDO** | https://github.com/googleapis/python-genai |

### Servidores públicos para demo

- **GitHub remoto:** `https://api.githubcopilot.com/mcp/`, OAuth ou PAT. Fonte: https://github.com/github/github-mcp-server . Já suporta a spec nova e mantém compatibilidade com clientes antigos. Fonte: https://github.blog/changelog/2026-07-23-github-mcp-server-supports-the-next-mcp-specification/
- **Context7:** `https://mcp.context7.com/mcp`, API key via `Authorization: Bearer`, ou OAuth em `/mcp/oauth`. Fonte: https://github.com/upstash/context7 . Era: **INFERIDO**.
- **Referência oficiais mantidos** (Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, Time): rodam via `npx`/`uvx`, não são hospedados. Google Drive, GitHub, Slack, Postgres etc. foram arquivados. Fonte: https://github.com/modelcontextprotocol/servers
- **Google Workspace oficial** (Gmail/Drive): ver ponto 2. Developer Preview.

### Recomendação

1. Usa o **SDK oficial `mcp` 2.x** como cliente. Ele é dual-era por declaração do README. O fluxo "usuário cadastra URL → `list_tools` → converte para schema de tool do provider → `call_tool`" é pouco código.
2. Não usa `langchain-mcp-adapters` agora. Ele está preso ao `mcp` 1.x (legacy). Servidor modern-only derruba ele.
3. Se o framework escolhido pelo agente `research-frameworks` já traz cliente MCP, confirma a era antes de adotar. Pydantic AI `MCPToolset` e Vercel `@ai-sdk/mcp` estão **INFERIDO** quanto à era.
4. Na demo, usa o servidor remoto do GitHub (compatível confirmado) e um servidor seu mínimo feito com `mcp` 2.x no mesmo compose. O servidor próprio é o plano B se um público falhar.
5. Suporta só Streamable HTTP. stdio num app multiusuário significa rodar processo arbitrário do usuário no servidor. É risco de segurança e escopo extra.

---

## 2. Conector Google Drive / Gmail

### Fatos

- **MCP oficial do Google:** Gmail `https://gmailmcp.googleapis.com/mcp/v1`, Drive `https://drivemcp.googleapis.com/mcp/v1`. Status **Developer Preview**. Exige projeto GCP, APIs e serviços MCP habilitados, OAuth client e **membresia no Google Workspace Developer Preview Program**. Escopos: `gmail.readonly`, `gmail.compose`, `drive.readonly`, `drive.file`. Fonte: https://developers.google.com/workspace/guides/configure-mcp-servers
- **MCP comunitário `taylorwilsdon/google_workspace_mcp`:** ~3.2k stars, desenvolvimento ativo, MIT. Streamable HTTP e stdio. OAuth 2.1 multiusuário com PKCE. Roda com `uvx workspace-mcp --tool-tier core` ou Docker. Fonte: https://github.com/taylorwilsdon/google_workspace_mcp
- **MCP de referência Google Drive:** arquivado. Fonte: https://github.com/modelcontextprotocol/servers
- **Classificação de escopos:**
  - `drive.file`: não-sensível. Google recomenda usar com Google Picker. Fonte: https://developers.google.com/workspace/drive/api/guides/api-specific-auth
  - `drive.readonly` e `drive`: restritos. Mesma fonte.
  - `gmail.readonly`, `gmail.compose`, `gmail.metadata`: restritos. `gmail.send`: sensível. Fonte: https://developers.google.com/workspace/gmail/api/auth/scopes
- **App em modo "Testing":**
  - Máximo 100 test users. **Só test users listados conseguem autorizar.** Google mostra aviso de app não verificado. Fonte: https://support.google.com/cloud/answer/15549945
  - Autorização expira em 7 dias, exceto se o app pede só perfil básico. Fonte: https://support.google.com/cloud/answer/15549945
  - Refresh token expira em 7 dias. Limite de 100 refresh tokens por conta por client ID; o mais antigo é invalidado sem aviso. Fonte: https://developers.google.com/identity/protocols/oauth2
  - Testing não exige verificação. Fonte: https://support.google.com/cloud/answer/13464323
- **Redirect URI:** HTTPS obrigatório (exceto localhost). Host não pode ser IP cru. TLD precisa estar na Public Suffix List. Sem wildcard. Fonte: https://developers.google.com/identity/protocols/oauth2/web-server
- **Tempo de setup do consent screen em Testing:** sem número oficial. Estimativa 20–40 min (criar projeto, habilitar APIs, consent screen, client, test users). **INFERIDO.**

### Armadilhas

- **Avaliador não conecta o próprio Gmail/Drive** se o e-mail dele não estiver na lista de test users. Isso quebra o bônus como fluxo self-service.
- Token morre em 7 dias. Se a avaliação acontecer depois disso, a conexão da demo precisa de novo consentimento.
- `1-2-3-4.sslip.io` como redirect URI: não é IP cru no formato, mas o Google pode rejeitar. **INFERIDO.** DuckDNS ou domínio próprio é mais seguro (ver ponto 4).
- MCP oficial do Google depende de aprovação num programa. Não cabe em 2 dias.

### Recomendação

1. Faz o conector direto com `google-api-python-client` e OAuth2 web flow. São 2–3 tools (buscar e-mails, ler e-mail, listar/ler arquivo do Drive). O token fica no Postgres, por usuário.
2. Escopos mínimos: `drive.file` com Google Picker se der tempo; senão `drive.readonly`. Para Gmail, `gmail.readonly`. Em Testing, restrito não exige verificação.
3. Trade-off da alternativa: rodar `google_workspace_mcp` como sidecar e registrar como servidor MCP entrega MCP e conector juntos. Custo: OAuth multiusuário passando pelo MCP, mais um container, 120+ tools poluindo o prompt (dá pra limitar com `--tool-tier core`). Recomendo o caminho direto; é menos peça móvel.
4. Para a avaliação: grava vídeo/prints com sua conta **e** pede os e-mails dos avaliadores para cadastrar como test users. Escreve isso no README.

---

## 3. Auth do app

### Fatos

- **Auth.js (NextAuth)** agora é mantido pelo time do Better Auth desde set/2025. Segue recebendo patches de segurança. **Better Auth é o recomendado para projeto novo.** Fonte: https://better-auth.com/blog/authjs-joins-better-auth
- **Better Auth + Postgres:** passa um `pg.Pool` na config; `npx auth@latest migrate` cria as tabelas. Fonte: https://www.better-auth.com/docs/adapters/postgresql
- **Better Auth → backend Python:** o plugin JWT expõe JWKS em `/api/auth/jwks`. O backend valida o token com a chave pública. A chave pode ser cacheada. Fonte: https://www.better-auth.com/docs/plugins/jwt
- **FastAPI-Users:** em modo manutenção. Só segurança e dependências, sem feature nova. Fonte: https://github.com/fastapi-users/fastapi-users
- **Supabase self-hosted:** 7 serviços principais + Postgres + Supavisor. Mínimo 4 GB RAM, 2 cores, 40 GB. Fonte: https://supabase.com/docs/guides/self-hosting/docker . Rodar só o GoTrue isolado: **INFERIDO**, a doc não cobre.
- **Clerk Hobby (grátis):** 50.000 MRU por app. Sem MFA e sem passkeys no free. Serviço externo. Fonte: https://clerk.com/pricing

### Encaixe por stack

| Opção | Next.js | Backend Python | Dados no seu Postgres |
|---|---|---|---|
| Better Auth | nativo | via JWKS | sim |
| Auth.js | funciona, sem feature nova | via JWT/sessão, mais manual | sim (adapter) |
| FastAPI-Users | — | nativo, manutenção | sim |
| Supabase Auth | sim | via JWT | pesado demais para o VPS |
| Clerk | nativo | via JWKS | não (externo) |

### Recomendação

1. Front Next.js: **Better Auth** com e-mail+senha e Google login opcional, no mesmo Postgres. Backend Python valida JWT pelo JWKS.
2. Backend Python puro sem Next.js: **FastAPI-Users** ainda resolve em 2 dias. Manutenção significa estável, não quebrado. Alternativa: sessão/JWT manual com hash argon2. É pouco código, mas é código seu de segurança.
3. Supabase self-hosted: não. Consome 4 GB só para ter auth.
4. Clerk: só se o tempo apertar muito. O avaliador pode ler como "terceirizou o requisito".

---

## 4. Deploy no VPS OCI

### Fatos

- **Caddy HTTPS automático** exige: registro A/AAAA apontando pro servidor, portas 80 e 443 abertas, diretório de dados persistente. Fonte: https://caddyserver.com/docs/automatic-https
- **OCI tem duas camadas de firewall:** Security List/NSG da VCN e iptables da imagem Ubuntu. Precisa abrir 80/443 nas duas. Não mexe nas regras da porta 3260. Fonte: https://blogs.oracle.com/developers/enabling-network-traffic-to-ubuntu-images-in-oracle-cloud-infrastructure
- **OCI Always Free (doc atual):** Ampere A1 = 1.500 OCPU-horas e 9.000 GB-horas/mês, equivalente a **2 OCPU e 12 GB** para tenancies Always Free. 200 GB de block storage. 10 TB/mês de saída. Instância ociosa é reclamada se, em 7 dias, CPU p95, rede e memória ficam abaixo de 20%. Fonte: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
  - O número clássico era 4 OCPU / 24 GB. A doc hoje diz 2/12. **O que vale é a sua instância:** roda `nproc` e `free -h`.
- **sslip.io / nip.io:** DNS curinga que resolve `1-2-3-4.sslip.io` para o IP. Os dois viraram o mesmo serviço. Let's Encrypt via HTTP-01 funciona. Sem wildcard. Fonte: https://nip.io/
  - **Nenhum dos dois está na Public Suffix List** (checado em https://publicsuffix.org/list/public_suffix_list.dat). Então todos os usuários dividem o limite de certificados do Let's Encrypt. O nip.io diz que o LE subiu o limite deles para 250.000. Fonte: https://nip.io/
  - Limite padrão do LE: 50 certificados por domínio registrado a cada 7 dias. Fonte: https://letsencrypt.org/docs/rate-limits/
- **DuckDNS:** DNS dinâmico grátis. `duckdns.org` **está** na Public Suffix List, então cada subdomínio tem cota própria no LE. Fontes: https://www.duckdns.org/ , https://publicsuffix.org/list/public_suffix_list.dat
- **Cloudflare Quick Tunnel (trycloudflare.com):** URL aleatória, máximo 200 requests simultâneos, **não suporta SSE**, só para teste, sem SLA. Fonte: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
  - Tunnel nomeado exige domínio gerenciado na Cloudflare. **INFERIDO** (a página consultada não diz).
- **CI:** `appleboy/ssh-action@v1` com `host`, `username`, `key`, `script`. Fonte: https://github.com/appleboy/ssh-action
- **Coolify:** mínimo 2 cores, 2 GB RAM, 10 GB. Suporta arm64. Fonte: https://coolify.io/docs/get-started/installation
- **Dokploy:** mínimo 2 GB RAM, 30 GB. Ocupa 80, 443 e 3000. Suporte ARM não documentado: **INFERIDO**. Fonte: https://docs.dokploy.com/docs/core/installation

### Recomendação

1. Stack: Docker Compose com `caddy`, `app` (ou `web` + `api`), `postgres`. Caddyfile de 3 linhas por host.
2. Domínio: **DuckDNS** (grátis, cota própria no LE, serve como redirect URI do Google). Se já tem domínio, usa subdomínio dele. sslip.io serve como plano B rápido.
3. Não usa Quick Tunnel. Chat com streaming usa SSE e o Quick Tunnel não suporta.
4. Abre 80/443 na Security List **e** no iptables antes de subir o Caddy. É o erro número um em OCI.
5. CI: GitHub Actions faz build da imagem (arm64 se o VPS for Ampere), publica no GHCR, e `ssh-action` roda `docker compose pull && docker compose up -d`. Coolify/Dokploy custa 2 GB de RAM e horas de setup; não compensa em 2 dias.
6. Build arm64 no runner x86 com QEMU é lento. Alternativa: `docker compose build` direto no VPS via SSH. **INFERIDO** qual é mais rápido no seu caso.

---

## 5. Auditoria e contagem de tokens

### Fatos

- **Langfuse self-hosted:** Postgres + ClickHouse + Redis/Valkey + S3 + web + worker. Docker Compose é "local use and testing". Recomenda 4 cores, 16 GiB, 100 GB. ARM não documentado. Fontes: https://langfuse.com/self-hosting , https://langfuse.com/self-hosting/deployment/docker-compose
- **Langfuse Cloud Hobby:** 50k units/mês, 30 dias de dados, 2 usuários, sem cartão. Fonte: https://langfuse.com/pricing
- **Langfuse captura:** tokens e custo automático para OpenAI, Anthropic e Google via integrações. Não infere custo de modelo de raciocínio sem contagem de tokens enviada. Fonte: https://langfuse.com/docs/observability/features/token-and-cost-tracking . Captura de tool call: **INFERIDO** (a página não cobre).
- **Logfire Personal (grátis):** 10M spans/mês, teto em $0, 30 dias, 1 seat + 2 guests read-only. Self-host só no Enterprise. Fonte: https://pydantic.dev/pricing
- **Logfire + Pydantic AI:** `instrument_pydantic_ai()` captura tokens por chamada, erros, cada tool call como span filho com argumentos e resultado, e a conversa completa. Custo em dinheiro: não confirmado. Fonte: https://pydantic.dev/docs/logfire/integrations/llms/pydanticai/
- **OpenTelemetry GenAI semconv** (`gen_ai.usage.input_tokens`, `gen_ai.tool.name`, span `execute_tool`) mudou para repositório próprio. Fonte: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/ . Status de estabilidade: **INFERIDO** (ainda em desenvolvimento).

### Recomendação

1. O requisito obrigatório é o **log de auditoria no app**. Faz uma tabela append-only `audit_events` no Postgres: `id`, `ts`, `user_id`, `conversation_id`, `event_type` (login, message_sent, llm_call, tool_call, share_created, share_revoked, connector_linked…), `payload jsonb`, `input_tokens`, `output_tokens`, `cost`, `latency_ms`, `model`.
2. Mostra essa tabela numa tela do app com filtro por usuário/conversa. O avaliador avalia o app, não o painel de um terceiro.
3. Append-only de verdade: o usuário do banco da aplicação sem `UPDATE`/`DELETE` nessa tabela. Custa um `REVOKE`. **INFERIDO** que o avaliador valoriza, mas é barato.
4. Tokens vêm do `usage` da resposta do provider. Não recalcula com tokenizer.
5. Tracing é bônus. Se o stack for Pydantic AI, Logfire free é uma linha e mostra tool calls. Aviso: os dados saem do VPS. Langfuse self-hosted no VPS: não, pede 16 GB.

---

## 6. Compartilhar conversa por link público

### Fatos

- **ChatGPT:** o link mostra o snapshot das mensagens no momento em que o link foi criado ou atualizado. Sem expiração configurável. Revogação apaga o link. Link pessoal é acessível por qualquer um que tem o link. Fonte: https://help.openai.com/en/articles/7925741-chatgpt-shared-links-faq
- **Claude:** o link mostra o snapshot com as mensagens anteriores ao compartilhamento. Mensagens posteriores ficam privadas. Tornar privado desativa o link. Compartilhar de novo atualiza o snapshot. Há uma tela que lista todos os links com opção de revogar. Fonte: https://support.claude.com/en/articles/10593882-share-and-unshare-chats
- Links públicos de chat já apareceram em buscador. Fonte (secundária): https://aident.ai/blog/claude-shared-chats-public-google

### Recomendação

1. Sem biblioteca. Uma tabela `shares`: `id` aleatório de ≥128 bits (ex. `secrets.token_urlsafe(16)`), `conversation_id`, `owner_id`, `last_message_id` (corte do snapshot), `created_at`, `revoked_at`.
2. Snapshot por corte (`last_message_id`), não cópia JSON. É mais simples e já cumpre "mensagens depois do share ficam privadas". Cópia JSON só se a conversa puder ser editada/apagada. **INFERIDO** que corte basta para o desafio.
3. Rota pública `/s/{id}` somente leitura, sem auth. Retorna 404 se `revoked_at` não é nulo. Mesmo 404 para id inexistente.
4. Header `X-Robots-Tag: noindex` na rota pública. Custa uma linha.
5. Grava `share_created`, `share_revoked` e (opcional) `share_viewed` no `audit_events`.
6. Tela "meus links" com botão revogar. É o que ChatGPT e Claude oferecem.
