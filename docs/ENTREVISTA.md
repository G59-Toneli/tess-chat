# Perguntas e respostas sobre as decisões

FAQ técnico. Para cada ADR: 3 perguntas prováveis e uma resposta curta. Cada resposta aponta a fonte; não decore o texto, entenda a fonte.

As perguntas mais duras vêm das divergências entre ADR e código. Elas estão marcadas **Lacuna**. Resposta honesta para lacuna: diga o que o código faz, por que ficou assim, e como corrige.

Antes de revisar, releia as funções do mapa de `REVISAR(human)` (funções marcadas para revisão humana) (revisadas em 24/09; a marca saiu do código). O mapa por módulo está em `docs/ESTRUTURA.md`.

## ADR 0001 — FastAPI + Pydantic AI

**Por que não LangGraph?**
LangGraph traz checkpointer pronto, mas a API é larga e menos tipada. Pydantic AI é fino: troca de provedor, tool tipada, cliente MCP, `RunUsage` e hook de histórico vêm de fábrica. Cada peça é explicável. Fonte: ADR 0001, `research/01`.

**Por que não fazer fork de um app pronto, como o LibreChat?**
Cobre quase tudo, mas é Node + Mongo e soa "instalei um app". A vaga avalia a lógica do backend em Python. O LibreChat ficou como contingência para 27/09 e não foi usado.

**Por que o histórico fica no seu banco e não na API de estado do Gemini?**
A Compactação é própria: preciso decidir o que vai ao modelo. Com o histórico no provedor, eu não controlo o corte. Também uso só a última mensagem do browser e leio o resto do Postgres, para o front não conseguir adulterar o histórico. Fonte: ADR 0001, DECISOES-AUTONOMAS (06).

## ADR 0002 — Front Vite servido pelo FastAPI

**Por que não Next.js?**
Seriam dois containers e dois deploys. O front é detalhe na vaga. Com Vite buildado, o FastAPI serve `web/dist` e tudo sobe num container só.

**`useChat` e AI Elements não prendem você na Vercel?**
Não. `useChat` é uma lib npm e fala um protocolo aberto de stream. O `VercelAIAdapter` do Pydantic AI emite esse protocolo. AI Elements são componentes shadcn copiados para o repo. Nada da Vercel roda no deploy.

**Como a SPA convive com as rotas da API?**
Catch-all na última linha de `main.py` (`app/estaticos.py`). `/api/*` sem rota devolve 404 JSON, não HTML. O resto cai no `index.html`. Fonte: DECISOES-AUTONOMAS (07a).

## ADR 0003 — gemini-3.8-flash no tier pago

**Por que não o Pro?**
Custa cerca de 3x e não mostra ganho visível numa demo. O Flash tem 1M de contexto, PDF e imagem nativos, tool calling paralelo e thinking configurável.

**Por que pagar se existe free tier?**
O free tier usa o conteúdo para treino e não publica limites. Usuário sobe PDF; não posso mandar isso para treino.

**E se o preço mudar?**
A Tabela de Preço tem data de vigência e é somente-inserção. Preço novo é linha nova. O Ledger guarda o preço aplicado em cada chamada, então o histórico não muda. Fonte: ADR 0003, migração 0005.

## ADR 0004 — Crédito em micro-dólar do uso real

**Por que micro-dólar inteiro e não float?**
Float erra na soma de centavos. Inteiro soma exato. Dinheiro, não token, porque token do Gemini e do Jev não se comparam. Fonte: `debit()` em `api/app/credito.py`.

**Thinking entra na conta? E o cache?**
Entram os dois, cada um com coluna própria na Tabela de Preço. No Gemini, `thoughts_token_count` vem separado de `candidates_token_count` (spike H4). No `RunUsage` o output já inclui thinking, então `debit()` tira o thinking do output e cobra ao preço de thinking. O input já inclui o cache, então input cobrado = input menos cache. Uma divisão só no fim, arredondada para cima: nunca cobra menos que o provedor. O uso vem do último chunk do stream, que é cumulativo. Fonte: `debit()` em `credito.py`, `spike/RESULTADO.md` H4.

**Lacuna: o ADR fala em estimativa, e dois pedidos juntos passam do Cap. Por quê?**
A reserva estima o input localmente, cerca de 3 caracteres por token, sem `count_tokens`. O ADR 0019 registra o porquê; veja a seção dele. A reserva não grava linha e não trava por Usuário, então duas chamadas simultâneas podem passar juntas. Correção: `SELECT ... FOR UPDATE` ou lock por Usuário na reserva. O acerto sempre usa o uso real. Fonte: LACUNAS, DECISOES-AUTONOMAS (08).

Pergunta extra provável: **turno cortado pelo teto de tools é cobrado?** Sim, desde o ticket 30: o `on_cancel` acerta o Ledger com o uso real e emite `tool_limit_reached` com o custo. Fonte: `api/app/chat.py`, ticket 30.

## ADR 0005 — Jev como Roteador

**Por que um Roteador antes do Gemini, se o Gemini já escolhe tool?**
Com confiança alta, forço a Tool (`ANY` + `allowedFunctionNames`) e o Gemini fica previsível. O Jev custa US$ 0,042 por 1M e responde em 70 a 500 ms. Abaixo do limiar, o Gemini decide (`AUTO`).

**E se o Jev errar ou cair?**
Abaixo do limiar a decisão volta ao Gemini. Erro do Jev vira `AUTO`, sem retry, com timeout de 5 s. `nenhuma` com confiança alta também vira `AUTO`: forçar "sem tool" não ganha nada. O golden set tem 10 frases: 9 certas, e a ambígua cai abaixo do limiar. Fonte: `apply_gate()` em `roteador.py`, `api/tests/fixtures/jev_golden.json`.

**Isso não abre espaço para prompt injection?**
O Roteador escolhe Tool, nunca permissão. Ele só vê o texto do turno e a lista de Tools já ativas na Conversa. Uma Tool desligada nunca entra nas opções.

## ADR 0006 — Compactação por Resumo

**Onde o corte cai, e como você não quebra um par tool-call e resultado?**
O corte cai sempre no início de um turno, numa linha `user`. Chamada e retorno de tool moram dentro da linha `assistant` do mesmo turno. Cortar antes de `user` nunca separa o par. Fonte: `ponto_de_corte()` em `compactacao.py`.

**O usuário perde as mensagens antigas?**
Não. As Mensagens originais ficam no banco e na tela. Só o que vai ao modelo muda. O Resumo fica na tabela `summaries`. Se o resumidor falhar, o turno segue com o histórico inteiro e grava `llm_error`.

**Lacuna: por que o marcador só aparece depois de recarregar?**
O front busca o ponto de corte uma vez por Conversa, e as Mensagens do stream nem têm id do banco. Foi YAGNI para a demo. Outras arestas: em turno com tool o gatilho soma todos os requests e pode disparar cedo; resumo de resumo não tem teste. Fonte: LACUNAS.

## ADR 0007 — Auditoria somente-inserção

**Como você garante que ninguém apaga um evento?**
Pelo banco, não pelo código. A app conecta como `tess_app`, que tem `REVOKE UPDATE, DELETE` em `audit_events`, `credit_ledger` e `price_table`. O Alembic roda como `tess_owner`. Fonte: `docker/postgres-init/01-roles.sql`, migrações 0001 e 0005.

**Por que não Langfuse ou Logfire?**
O que se avalia é o app, não um painel de terceiro. Langfuse self-hosted pede 16 GB. A tela `/auditoria` é o painel de observabilidade.

**Por que Ledger e auditoria em tabelas separadas?**
Uma é dinheiro, a outra é história. O saldo é a soma do Ledger; misturar com eventos de login deixaria a soma frágil. Usuário comum vê só os próprios eventos; admin vê todos. Fonte: `auditoria.py`.

## ADR 0008 — Compartilhamento por corte

**Por que não copiar as Mensagens para o link?**
A Conversa não é editável e `messages.id` só cresce. Guardar o maior id no momento do share basta: a leitura filtra `id <= corte`. Mensagem nova fica fora do link.

**Por que revogado e inexistente dão o mesmo 404?**
Quem tem um link revogado não descobre que ele existiu. Mesmo corpo, mesmo header. Fonte: `shares.py`.

**O link público vaza o quê?**
Só texto de Mensagens de usuário e assistente. Resultado de tool fica fora, porque pode ter dado de terceiro. O autor aparece só pela parte do e-mail antes do `@`. Id de 128 bits, header `X-Robots-Tag: noindex`. Fonte: DECISOES-AUTONOMAS (13).

## ADR 0009 — Registro único de Tools e cliente MCP

**Por que não usar a busca embutida do Gemini?**
Ela não passa pelo registro: sem toggle por Conversa e sem evento de auditoria. `web_search` (Tavily) e `web_fetch` (Jina, com fallback trafilatura) são nossas. A auditoria é um wrapper (`Auditada`) em volta do toolset, então Tool nova, inclusive MCP, é auditada sem código extra.

**Por que só Streamable HTTP e não stdio?**
stdio num app multiusuário é executar processo arbitrário no servidor, escolhido pelo usuário.

**Lacuna: e se o Servidor MCP cair, ou apontar para rede interna?**
Hoje o servidor que cai depois do cadastro derruba o turno das Conversas do dono. Contorno: desligar em `/mcp`. A URL é livre, então há risco de SSRF. O ticket 23 corrige os dois: testar o servidor com timeout curto no turno e seguir sem as tools dele; resolver o DNS no cadastro e recusar IP privado e link-local. Fonte: DECISOES-AUTONOMAS (17).

Pergunta extra provável: **como dois Usuários cadastram o mesmo servidor sem colidir nome de tool?** Nome no registro = slug do servidor + 4 hex do id + tool. Fonte: `prefixo()` em `mcp.py`.

## ADR 0010 — Conector Google por OAuth direto

**Por que não o MCP oficial do Google?**
É Developer Preview com programa fechado. Conector é credencial do Usuário com tools nossas. MCP é provedor externo de tools. São conceitos diferentes e o app tem os dois.

**Lacuna: o ADR diz `google-api-python-client` e o código usa `httpx`. Por quê?**
A lib do Google é síncrona sobre httplib2 e não passa pelo transporte injetável dos testes. Com `httpx`, os testes mockam o Google igual às outras tools. A decisão do ADR, OAuth direto, ficou igual; mudou só a biblioteca. Fonte: DECISOES-AUTONOMAS (18).

**Como você protege o token e o callback?**
Tokens cifrados com Fernet; a chave (`CONNECTORS_KEY`) fica fora do banco. O callback chega por GET do browser sem o Bearer, então o `state` é um JWT assinado com o id do Usuário e 10 min de validade: identifica o dono e barra CSRF. Refresh 60 s antes de vencer; sem refresh válido, a tool responde "reconecte em Conectores". Fonte: `conectores.py`.

Pergunta extra provável: **testou com Gmail real?** Os testes usam Google mockado. A validação real depende do seu login e está no `MANHA.md`. Responda com o que foi feito até a data.

## ADR 0011 e 0014 — Compose, nginx do host, domínio próprio

**Por que não serverless?**
INFERIDO, nenhum doc compara. O chat é stream SSE longo com vários requests ao modelo por turno; serverless tem timeout e cobra por duração. Os Anexos ficam em disco. Fonte: MOTIVACOES §4.

**Por que não Cloudflare Tunnel ou ngrok?**
O Quick Tunnel não passa SSE e mata o streaming. ngrok tem URL efêmera e tela intermediária. Coolify e Dokploy pedem 2 GB de RAM e horas de setup.

**Por que não Kubernetes?**
INFERIDO. Um app, um banco, uma semana no ar. Compose descreve três serviços num arquivo. Nada pede escala nem alta disponibilidade.

**Por que saiu o Caddy?**
A conta OCI nova falhou e o deploy foi para o VPS compartilhado. Lá o nginx do host já ocupa 80/443 com certbot e serve outra produção. Um Caddy nosso precisaria dessas portas. O nginx ganhou um site novo com `proxy_buffering off` para o SSE passar. Fonte: ADR 0014.

Estado: no ar em https://chat.toneli.dev.br. CI por GitHub Actions faz o deploy por ssh em push na `main`.

## ADR 0012 — Retry e fallback de modelo

**O que é erro transitório para você?**
429, 500, 502, 503, 504, timeout e erro de API sem status. Outro 4xx é erro do request: repetir ou trocar de modelo só gasta. A mesma regra vale para o retry e para o `fallback_on`. Fonte: `transitorio()` em `resiliencia.py`.

**Por que o retry não repete o stream que já começou?**
Parte do texto já foi para o browser. Repetir duplicaria. Só a abertura do stream repete; falha no meio vira chunk de erro. Por isso o front não mostra "tentando de novo": o retry acontece antes do stream abrir.

**O ADR promete OpenAI no fallback. Cadê?**
Saiu. O ADR 0018 revisa este: a cadeia é só `gemini-3.8-flash` e depois `gemini-3.7-flash`. Veja a seção do 0018. Aresta que ficou: com o 3.8 fora, cada request tenta 3 vezes antes de trocar, e turno com tool fica lento. Fonte: ADR 0018, LACUNAS.

## ADR 0013 — Envio de e-mail só com confirmação

**Por que o modelo não envia direto, se ele já decide chamar a tool?**
E-mail enviado não volta. O modelo erra destinatário, tom e conteúdo, e o Roteador e o prompt não são trilho para ação irreversível. A tool `gmail_send` só grava um Rascunho `pendente`. O único caminho que chama `messages/send` é `POST /api/connectors/google/drafts/{id}/enviar`, autenticado pelo dono. Fonte: ADR 0013, `conectores.py`.

**Por que confirmar por clique e não pelo texto "pode enviar"?**
Confirmação por texto põe o modelo para decidir se a frase é um sim. Erro de interpretação vira e-mail enviado. Com clique, o modelo nem tem tool de envio final: um teste manda "pode enviar" no chat e confere que o Rascunho segue `pendente` e o Gmail não recebe nada. Dois cliques simultâneos também não enviam duas vezes: o endpoint trava a linha (`SELECT ... FOR UPDATE`) e o segundo recebe 409. Fonte: `test_email.py`.

**O Pydantic AI tem `requires_approval` (deferred tools). Por que não usou?**
Com `requires_approval`, a tool não executa: o run encerra e devolve `DeferredToolRequests` como output. Para seguir, é preciso um run novo com o `message_history` e o `deferred_tool_results` (`ToolApproved` ou `ToolDenied`). Aprovado ou negado, o resultado volta ao modelo: mais uma chamada paga só para ele dizer "enviado". O `HandleDeferredToolCalls` resolve dentro do mesmo run, mas para esperar um clique seguraria o stream SSE aberto; recarregou a página, perdeu. O Rascunho é linha no banco: sobrevive a recarregar a página, tem estado próprio (`pendente|enviado|descartado`), auditoria própria e um endpoint que chama o Gmail sem passar pelo modelo. Qualquer tool futura com escrita externa pode copiar. Fonte: ADR 0013, seção Consequências; `pydantic_ai/_deferred.py` e `capabilities/deferred_tool_handler.py` (pydantic-ai-slim 2.47.0).

Pergunta extra provável: **como responde na mesma thread?** `gmail_read` devolve `thread_id`. Com ele, `gmail_send` lê o `Message-ID` da última mensagem da thread e grava `In-Reply-To` e `References` no Rascunho; o envio manda `threadId` e esses cabeçalhos no MIME.

## ADR 0017 — Conector Google com as libs oficiais de auth

**Por que trocou o `httpx` puro pelas libs do Google?**
Decisão do ticket 43: OAuth e refresh passam para `google-auth` e `google-auth-oauthlib` (`Flow`), com PKCE ligado e `code_verifier` em cookie httpOnly. Lib oficial trata refresh, expiração e `RefreshError` do jeito que o Google documenta; eu não mantenho esse código. Fonte: ADR 0017.

**Então por que Gmail e Drive seguem em `httpx`?**
O `google-api-python-client` está em maintenance mode, roda sobre `google-auth-httplib2` (deprecated pelo Google) e é síncrono. Não existe cliente oficial async para Gmail e Drive. Por isso o caminho é híbrido: lib oficial na auth, `httpx` async nas APIs. Fonte: ADR 0017.

**O que o PKCE protege, se já tem `state` assinado?**
O `state` barra CSRF e identifica o dono. O PKCE prende o `code` a quem começou o fluxo: um `code` vazado não troca por token sem o `code_verifier`, que só existe no cookie. Fonte: ADR 0017, ticket 41.

## ADR 0018 — Fallback só entre modelos Gemini

**Por que não tem fallback para outro provedor?**
Não há chave OpenAI. Código para um provedor sem chave é código morto: precisaria de preço na Tabela de Preço e de teste do stream de outro provedor, para um cenário que a demo não exercita. Fica retry com backoff e a cadeia `gemini-3.8-flash` → `gemini-3.7-flash`. Fonte: ADR 0018, `api/app/resiliencia.py`.

**E se o Google inteiro cair?**
O chat cai. Os dois modelos dependem do mesmo provedor e da mesma chave. É risco aceito e escrito. Voltar a ter terceiro provedor pede ADR novo. Fonte: ADR 0018.

**Por que escrever ADR para tirar uma coisa?**
O ADR 0012 prometia OpenAI e o código não fazia. Documento que diverge do código é pergunta sem resposta. O 0018 alinha os dois. Fonte: ADR 0012 (status), ADR 0018.

## ADR 0019 — Reserva por estimativa local

**Por que não usa `count_tokens`, se ele dá o número exato?**
A reserva só segura crédito. A cobrança final usa o `usage` real (ADR 0004). `count_tokens` custaria uma ida de rede por turno antes do primeiro token e seria mais um ponto de falha, cujo fallback seria a própria estimativa. Fonte: ADR 0019.

**O spike H5 provou que `UsageLimits(count_tokens_before_request=True)` funciona. Por que não usou?**
Provou que funciona, não que compensa. Tem o mesmo custo de rede, limita tokens e não dinheiro, e o `FunctionModel` dos testes não implementa. Fonte: DECISOES-AUTONOMAS (08), `spike/py/h5_runusage.py`.

**Quanto a estimativa erra?**
Não medido. A razão ~3 caracteres por token é INFERIDA; imagem soma `TOKENS_IMAGEM` fixo. O erro só afeta turno perto do Cap: pode recusar um que caberia ou aceitar um que passa um pouco. O acerto grava o valor real. Fonte: `_estimar_input` em `api/app/chat.py`.

## ADR 0022 — Servidor MCP por OAuth (descoberta, DCR, PKCE)

**Como o app sabe se o servidor tem OAuth, se o usuário só cola a URL?**
Manda um `initialize` sem token. Se vier 2xx, o servidor é aberto e o app cadastra direto. Se vier 401 com `WWW-Authenticate`, o app lê o metadata do recurso (RFC 9728) e depois o do authorization server (RFC 8414). Com `registration_endpoint`, abre o consentimento; sem ele, pede um token. O `iniciar` devolve `modo` = `oauth`, `sem_auth` ou `token`. Fonte: `iniciar` e `_descobrir` em `mcp_oauth.py`.

**O que é DCR e por que só DCR?**
Dynamic Client Registration (RFC 7591): o app se registra sozinho no provedor e recebe um `client_id` na hora, sem cadastro manual. Notion, Stripe, Linear e Atlassian aceitam. Sem DCR (GitHub, Slack, HubSpot), eu teria que registrar um app em cada provedor, guardar o segredo no `.env` e manter o redirect por ambiente. Para esses, o token no header continua funcionando. Fonte: ADR 0022, item 3.

**Por que não usou o `OAuthClientProvider` do SDK MCP?**
Ele roda o fluxo inteiro numa coroutine que fica esperando o callback. Num web app, o authorize e o callback são dois requests HTTP. Eu teria que guardar um `{state: Future}` em memória, que some num restart. Fiz os dois requests à mão, como no conector Google (ADR 0017), e usei do SDK só os modelos e os helpers de URL. Fonte: ADR 0022, alternativas.

**Onde fica o estado entre o authorize e o callback?**
Num cookie httpOnly, cifrado com Fernet, com `path` só no callback: `code_verifier`, nome, URL e o cliente do DCR. O state JWT leva o usuário e um `nonce` que também está no cookie; o callback só aceita o par que bate. O banco só recebe a linha depois da troca do code. Antes era gravada no `iniciar`, e o consentimento abandonado deixava um card "aguardando" (ticket 57). Fonte: `_concluir` em `mcp_oauth.py`.

**E o SSRF, se o metadata vem de um servidor remoto?**
Toda URL que vem de metadata (recurso, authorization server, registration, authorize, token) passa por `validar_url` antes do request. Sem isso, um servidor público apontaria o `token_endpoint` para a rede interna. Fonte: ADR 0022, item 5.

**Como o token é renovado?**
Antes do turno, `renovar` troca o token que vence em menos de 60 s, mandando `resource` (RFC 8707). Refresh que falha grava `expirado`, e o servidor sai do turno (fail-closed), como na Tess. O Bearer novo é gravado na coluna `headers` que já existia, então o cliente MCP do turno não mudou. Fonte: `renovar` em `mcp_oauth.py`.

**Lacunas:** cada clique registra um app novo no provedor (DCR sem reaproveitamento). Remover não revoga o token no provedor. DNS rebinding não coberto. Fonte: `docs/LACUNAS.md`.

Pergunta extra provável: **testou de verdade?** Sim, em produção: Notion e Stripe conectados por OAuth, e um turno de chat chamou 9 tools do Notion. O Linear chegou à tela de consentimento, o DeepWiki conectou sem auth e o GitHub caiu no modo token.

## ADR 0024 — Tool por API

**O que é, em uma frase?**
O usuário transforma uma API HTTP numa Tool preenchendo um formulário: URL com `{parametros}`, descrição de cada um, autenticação e um exemplo. O app testa com o exemplo e só salva se a API responder 2xx. Fonte: `api_tools.py`, `web/src/pages/ApiTools.tsx`.

**Por que request HTTP declarativo e não deixar o usuário escrever código?**
Código do usuário exige sandbox: processo isolado, limite de CPU e memória, rede filtrada. É uma superfície de ataque inteira nova. Um request declarativo cobre o caso comum, que é uma API REST com parâmetros, e reaproveita a barreira de SSRF que já existe. Fonte: ADR 0024, "Por quê".

**Por que testar antes de salvar?**
É o mesmo invariante do cadastro de MCP. Uma tool salva e quebrada só aparece no meio de um turno, e o modelo gasta crédito para descobrir. Testando no cadastro, o erro aparece na hora, para quem pode corrigir. Mudar qualquer campo depois do teste desliga o Salvar.

**Por que não tem edição?**
Editar exigiria testar de novo, trocar o schema de uma Tool que pode estar em Conversas abertas e decidir o que fazer com o segredo guardado. Remover e cadastrar de novo cobre isso com o que já existe.

**Como impede que um parâmetro mude o destino do request?**
Os valores são URL-encoded (`quote(safe="")`), então `/` ou `?` num valor não muda a rota. Placeholder no host é recusado no cadastro. `validar_url` roda na URL final e em cada redirect, até 3 saltos. Fonte: ADR 0024, item 5 e decisões autônomas.

**Onde fica o token da API?**
Cifrado com Fernet (`CONNECTORS_KEY`). Não volta na listagem nem aparece no Evento de auditoria. No E2E de 23/09, conferi os 18 eventos da conta de teste no banco: nenhum tinha o token.

**Por que não importar OpenAPI?**
Cobre API grande, mas usuário não técnico não tem o spec à mão, e a maioria das APIs públicas simples não publica um.

**Lacunas:** segredo colado na URL (`?key=...`) não é tratado como segredo. Header de auth por nome segue num redirect para outro host. DNS rebinding não coberto. Fonte: ADR 0024, consequências.

Pergunta extra provável: **a Tess tem isso?** A documentação dela lista "Custom API" como *Coming soon* (docs.tess.im/en/connectors.md). Validado em produção com ViaCEP, Open-Meteo, CNPJ e feriados (BrasilAPI) sem auth, e com GitHub (Bearer, GET) e Tavily (Bearer, POST com corpo).

## Workflow com IA

**Como o projeto foi construído?**
Um orquestrador, uma sessão do Claude Code, escolhe o próximo ticket livre e dispara um agente Opus por ticket, às vezes em paralelo. O agente segue um prompt-padrão, faz TDD, commita e reporta. O orquestrador confere, dá push e encerra o agente. Você decide ADRs e glossário e escreveu os tickets do plano. O orquestrador abriu tickets de ajuste (20 a 23) a partir de ressalvas dos agentes. Fonte: `docs/WORKFLOW.md`, `docs/AGENT-PROMPT.md`.

**O que é um ticket aqui?**
Fatia vertical com contexto, o que construir, aceite testável e dependências (`Blocked by`). Fecha com uma seção `## Answer` e uma linha no `LEDGER.md` com testes e chamadas reais. Fonte: `.scratch/desafio/issues/`.

**O que é `REVISAR(human)`, e por que o agente decidiu coisas sem você?**
No plano, você escreveria três funções e o agente pararia diante de decisão nova. Isso travava a noite. Desde 23/09 o agente implementa, marca a função com `REVISAR(human)` e registra a decisão, a alternativa e o porquê em `DECISOES-AUTONOMAS.md`. A troca foi velocidade agora e estudo depois. Arquitetura continua só por ADR.

**Como você controla custo e qualidade do que o agente fez?**
Teto de chamadas reais por ticket, registrado no LEDGER. Testes com resposta gravada ou modelo de teste do Pydantic AI. Integração contra Postgres real. Teste de mutação nas regras críticas. Suíte completa em lote no fim do bloco. Front fecha com screenshot.

**O que deu errado?**
O plano era um script externo chamando `claude -p` com a suíte como gate fora do Claude. Na prática rodou um orquestrador com agentes paralelos no mesmo working tree. Custo: o gate externo sumiu, e o stage compartilhado fez um commit engolir arquivos de outro ticket (`2c738a6`). Regras novas: `git commit --only` com os próprios arquivos e um agente por vez em `chat.py`. O motivo da troca não está escrito (INFERIDO: paralelismo e correção de rumo entre tickets). Fonte: `docs/WORKFLOW.md`, MOTIVACOES §5.

**Por que assim?**
Você precisa defender cada decisão. Por isso arquitetura só entra por ADR, e toda decisão de agente fica escrita com a alternativa descartada. O resto é execução, e execução pode ser delegada.
