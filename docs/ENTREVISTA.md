# Guia de entrevista

Para o Toneli se preparar. Para cada ADR: 3 perguntas prováveis e uma resposta curta. Cada resposta aponta a fonte; não decore o texto, entenda a fonte.

As perguntas mais duras vêm das divergências entre ADR e código. Elas estão marcadas **Lacuna**. Resposta honesta para lacuna: diga o que o código faz, por que ficou assim, e como corrige.

Antes da entrevista, leia as funções marcadas `REVISAR(human)`: `grep -rn "REVISAR(human)" api/app`. O mapa por módulo está em `docs/ESTRUTURA.md`.

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
O free tier usa o conteúdo para treino e não publica limites. Avaliador sobe PDF; não posso mandar isso para treino.

**E se o preço mudar?**
A Tabela de Preço tem data de vigência e é somente-inserção. Preço novo é linha nova. O Ledger guarda o preço aplicado em cada chamada, então o histórico não muda. Fonte: ADR 0003, migração 0005.

## ADR 0004 — Crédito em micro-dólar do uso real

**Por que micro-dólar inteiro e não float?**
Float erra na soma de centavos. Inteiro soma exato. Dinheiro, não token, porque token do Gemini e do Jev não se comparam. Fonte: `debit()` em `api/app/credito.py`.

**Thinking entra na conta? E o cache?**
Entram os dois, cada um com coluna própria na Tabela de Preço. No Gemini, `thoughts_token_count` vem separado de `candidates_token_count` (spike H4). No `RunUsage` o output já inclui thinking, então `debit()` tira o thinking do output e cobra ao preço de thinking. O input já inclui o cache, então input cobrado = input menos cache. Uma divisão só no fim, arredondada para cima: nunca cobra menos que o provedor. O uso vem do último chunk do stream, que é cumulativo. Fonte: `debit()` em `credito.py`, `spike/RESULTADO.md` H4.

**Lacuna: o ADR fala em estimativa, e dois pedidos juntos passam do Cap. Por quê?**
A reserva estima o input localmente, cerca de 3 caracteres por token, sem `count_tokens`. Motivo: `count_tokens` custa um request extra por turno e o modelo de teste não implementa. A reserva não grava linha e não trava por Usuário, então duas chamadas simultâneas podem passar juntas. Correção: `SELECT ... FOR UPDATE` ou lock por Usuário na reserva. O acerto sempre usa o uso real. Fonte: LACUNAS, DECISOES-AUTONOMAS (08).

Pergunta extra provável: **turno cortado pelo teto de tools é cobrado?** Não. É lacuna aberta (06b).

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
O avaliador avalia o app, não um painel de terceiro. Langfuse self-hosted pede 16 GB. A tela `/auditoria` é o painel de observabilidade.

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

## ADR 0011 — Compose + Caddy + domínio próprio

**Por que não serverless?**
INFERIDO, nenhum doc compara. O chat é stream SSE longo com vários requests ao modelo por turno; serverless tem timeout e cobra por duração. Os Anexos ficam em disco. Fonte: MOTIVACOES §4.

**Por que não Cloudflare Tunnel ou ngrok?**
O Quick Tunnel não passa SSE e mata o streaming. ngrok tem URL efêmera e tela intermediária. Coolify e Dokploy pedem 2 GB de RAM e horas de setup.

**Por que não Kubernetes?**
INFERIDO. Um app, um banco, uma semana no ar. Compose descreve três serviços num arquivo. Nada pede escala nem alta disponibilidade.

Estado: o deploy é o ticket 16, bloqueado no acesso SSH ao VPS.

## ADR 0012 — Retry e fallback de modelo

**O que é erro transitório para você?**
429, 500, 502, 503, 504, timeout e erro de API sem status. Outro 4xx é erro do request: repetir ou trocar de modelo só gasta. A mesma regra vale para o retry e para o `fallback_on`. Fonte: `transitorio()` em `resiliencia.py`.

**Por que o retry não repete o stream que já começou?**
Parte do texto já foi para o browser. Repetir duplicaria. Só a abertura do stream repete; falha no meio vira chunk de erro. Por isso o front não mostra "tentando de novo": o retry acontece antes do stream abrir.

**Lacuna: o ADR promete OpenAI no fallback. Cadê?**
Não está implementado. A cadeia é `gemini-3.8-flash` e depois `gemini-3.7-flash`; nada lê `OPENAI_API_KEY`. Ativar pede a chave, o modelo na cadeia e a linha de preço na Tabela de Preço. Outra aresta: com o 3.8 fora, cada request tenta 3 vezes antes de trocar, e turno com tool fica lento. Fonte: `api/app/chat.py`, LACUNAS.

## Workflow com IA

**Como o projeto foi construído?**
Um orquestrador, uma sessão do Claude Code, escolhe o próximo ticket livre e dispara um agente Opus por ticket, às vezes em paralelo. O agente segue um prompt-padrão, faz TDD, commita e reporta. O orquestrador confere, dá push e encerra o agente. Você decide ADRs, glossário e tickets. Fonte: `docs/WORKFLOW.md`, `docs/AGENT-PROMPT.md`.

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
