# Spike 01: resultado

Execução: 2026-09-22 21:54 a 22:15 (-03), Windows 11, máquina local do Toneli.
Ambiente: Python 3.14.3 (uv 0.12.1), Node 24.13.1, Docker Compose v5.1.4, Docker Engine 29.5.3.
Postgres 17 via `spike/docker-compose.yml`, host `127.0.0.1:5433`, banco `spike`.
Chave Gemini usada: `GEMINI_PAID_API_KEY`, passada explícita em todo construtor.
Evidência bruta: `spike/out/`. Scripts: `spike/py/`. Front: `spike/web/`.

| # | Hipótese | Veredito |
|---|---|---|
| 1 | Resolução de dependências Python | PASSOU |
| 2 | VercelAIAdapter → useChat | PASSOU |
| 3 | AI Elements em Vite | PASSOU (com ressalva de setup) |
| 4 | usage_metadata no stream do Gemini | PASSOU |
| 5 | RunUsage do Pydantic AI com Google | PASSOU |
| 6 | Built-in + function declaration | PASSOU (exige flag) |
| 7 | Era do cliente MCP | PASSOU (só era moderna observada) |
| 8 | FastAPI-Users | PASSOU |
| 9 | Jev em português | PASSOU |

Custo das chamadas:

| Provedor | Chamadas | Observação |
|---|---|---|
| Gemini pago | 17 | inclui 5 `countTokens` da H5 e 2 chamadas perdidas num `TypeError` do script |
| Jev | 10 | uma por frase |

---

## 1. Resolução de dependências Python: PASSOU

`uv add pydantic-ai "fastapi-users[sqlalchemy]" "mcp>=2" google-genai typesafe-sdk` resolveu em Python 3.14.3 sem conflito. Não foi preciso Python 3.12.

Pydantic AI não pina `mcp` direto. O extra `mcp` de `pydantic-ai-slim` puxa `fastmcp-slim[client]>=3.3.0,<5`. O `fastmcp-slim` 4.0.5 pina `mcp>=2.0.0,<3.0.0`.

```
mcp v2.2.0
├── spike v0.1.0
└── fastmcp-slim v4.0.5 (extra: client)
    └── pydantic-ai-slim[client] v2.47.0 (extra: mcp)
        └── pydantic-ai[anthropic, cli, evals, google, logfire, mcp, openai, web] v2.47.0
```

Duas pilhas HTTP convivem. `google-genai` usa `httpx<1.0` (0.28.1). O resto usa `httpx2` 2.13.0. Não conflitam.

Versões resolvidas (`uv pip list`, lista completa em `out/h1_uv_pip_list.txt`):

| Pacote | Versão |
|---|---|
| pydantic-ai / pydantic-ai-slim | 2.47.0 |
| pydantic | 2.13.5 |
| fastapi | 0.141.1 |
| starlette | 1.6.0 |
| fastapi-users | 15.0.5 |
| fastapi-users-db-sqlalchemy | 7.0.0 |
| sqlalchemy | 2.0.54 |
| asyncpg | 0.31.0 (adicionado para a H8) |
| mcp / mcp-types | 2.2.0 |
| fastmcp-slim | 4.0.5 |
| google-genai | 2.25.0 |
| typesafe-sdk | 0.7.1 |
| uvicorn | 0.53.0 |
| httpx / httpx2 | 0.28.1 / 2.13.0 |

---

## 2. VercelAIAdapter → useChat: PASSOU

Endpoint: `spike/py/h2_server.py`, `VercelAIAdapter.dispatch_request(request, agent=agent, sdk_version=7)`.
Front: `spike/web/src/App.tsx`, `useChat` com `DefaultChatTransport({ api: '/api/chat' })`, proxy Vite `/api` → `127.0.0.1:8000`.

`curl` com `TestModel` (zero custo), `out/h2_curl_testmodel.txt`:

```
HTTP/1.1 200 OK
x-vercel-ai-ui-message-stream: v1
content-type: text/event-stream; charset=utf-8

data: {"type":"start"}
data: {"type":"start-step"}
data: {"type":"text-start","id":"a5a2a916-..."}
data: {"type":"text-delta","delta":"Ola ","id":"a5a2a916-..."}
data: {"type":"text-delta","delta":"Toneli, ","id":"a5a2a916-..."}
... (11 text-delta)
data: {"type":"text-end","id":"a5a2a916-..."}
data: {"type":"message-metadata","messageMetadata":{"pydantic_ai":{"timestamp":"2026-09-23T01:10:38.187324Z"}}}
data: {"type":"finish-step"}
data: {"type":"finish"}
data: [DONE]
```

Browser (Playwright, Vite dev em `localhost:5173`, backend com `gemini-3.8-flash`), `out/h2_browser.txt`. O texto da mensagem do assistente cresceu em 5 passos no DOM:

| t desde o envio (ms) | caracteres |
|---|---|
| 7261 | 121 |
| 7276 | 219 |
| 7325 | 294 |
| 7402 | 434 |
| 7456 | 506 |

Os ~7 s antes do primeiro texto são INFERIDO como thinking do modelo. O endpoint não configurou thinking; o default não foi medido.

---

## 3. AI Elements em Vite: PASSOU (com ressalva de setup)

`npx ai-elements@latest add conversation message prompt-input` instalou e `npm run build` passou. Os componentes renderizaram no browser na H2.

Ressalvas encontradas:

1. **`shadcn init -d` gera base Base UI (`style: base-nova`).** Com ela, `prompt-input.tsx` do AI Elements não compila: 7 erros TS (`BaseUIEvent` incompatível, `openDelay`/`closeDelay` inexistentes). Correção: `npx shadcn@latest init -t vite -b radix -p nova -f`. Resultado: `style: radix-nova`, build limpo.
2. **`ai-elements add --yes`** trata `--yes` como nome de componente e falha. Rodar sem flag.
3. **TypeScript 6.0.3** recusa `baseUrl` (TS5101). Usar só `paths`.
4. `tooltip` exige `TooltipProvider` em volta do app.
5. Bundle principal: 1,59 MB (486 kB gzip), por causa de `streamdown` (shiki, mermaid). Só aviso do Vite, não erro.
6. `@base-ui/react` ficou como dependência órfã do primeiro init. Não afeta o build.

Saída do build (`out/h3_build.txt`):

```
dist/assets/index-64seIsr4.js   1,591.53 kB │ gzip: 485.87 kB
(!) Some chunks are larger than 500 kB after minification.
✓ built in 2.06s
```

Versões (`npm ls --depth=0`, completo em `out/web_npm_ls.txt`):

| Pacote | Versão |
|---|---|
| ai | 7.0.111 |
| @ai-sdk/react | 4.0.114 |
| react / react-dom | 19.3.0 |
| vite | 8.3.0 |
| typescript | 6.0.3 |
| tailwindcss / @tailwindcss/vite | 4.3.3 |
| shadcn | 4.21.0 |
| radix-ui | 1.6.7 |
| streamdown | 2.6.0 |

Fallback do ticket (shadcn puro + useChat): não necessário.

---

## 4. usage_metadata no stream do Gemini: PASSOU

Script: `spike/py/h4_usage_stream.py`. Modelo `gemini-3.8-flash`, `ThinkingConfig(thinking_level="high")`.
Prompt: "Um trem sai as 9h a 80 km/h e outro as 10h a 120 km/h no mesmo sentido. Que horas o segundo alcanca o primeiro? Responda curto."

Respostas:

1. **Em quais chunks `usage_metadata` aparece?** Em todos. O valor é cumulativo. O último chunk tem o total final.
2. **`thoughts_token_count` está dentro de `candidates_token_count`?** Não. É separado. `total = prompt + candidates + thoughts`.

Números brutos (`out/h4_high.txt`):

| Origem | chunk | prompt | candidates | thoughts | total | prompt+candidates | prompt+candidates+thoughts |
|---|---|---|---|---|---|---|---|
| stream | 0 | 48 | 13 | 370 | 431 | 61 | 431 |
| stream | 1 (último, texto vazio) | 48 | 13 | 370 | 431 | 61 | 431 |
| não-stream | — | 48 | 13 | 464 | 525 | 61 | 525 |

Rodada anterior com `thinking_level="low"` e prompt trivial (`out/h4.txt`): o modelo não gerou thinking. O campo `thoughts_token_count` veio ausente, não zero. O usage também veio cumulativo em todos os 4 chunks:

| Origem | chunk | prompt | candidates | thoughts | total |
|---|---|---|---|---|---|
| stream | 0 | 17 | 20 | ausente | 37 |
| stream | 1 | 17 | 45 | ausente | 62 |
| stream | 2 | 17 | 47 | ausente | 64 |
| stream | 3 | 17 | 47 | ausente | 64 |
| não-stream | — | 17 | 48 | ausente | 65 |

O código do Pydantic AI confirma: "Gemini streams usage as cumulative snapshots" (`pydantic_ai/models/google.py`, ~linha 2116).

Consequência para o ADR 0004: pegar o usage do último chunk. Não somar chunks. Cobrar output = candidates + thoughts.

---

## 5. RunUsage do Pydantic AI com Google: PASSOU

Scripts: `spike/py/h5_runusage.py`, `spike/py/h5_cache.py`. Mesmo prompt da H4, `google_thinking_config={"thinking_level": "high"}`.

Respostas:

1. **Thinking separado?** Sim. `RunUsage.details['thoughts_tokens']`. No `RequestUsage` também vem `output_reasoning_tokens`. Atenção: `RunUsage.output_tokens` já soma candidates + thoughts.
2. **Cache separado?** Sim. `RunUsage.cache_read_tokens` e `details['cached_content_tokens']`. Provado com cache implícito num prompt de 7.876 tokens repetido.
3. **`UsageLimits(count_tokens_before_request=True)` funciona com Google?** Sim. `GoogleModel` implementa `count_tokens`. Com `input_tokens_limit=5` a execução foi recusada antes de gerar.

Números brutos (`out/h5.txt`, `out/h5_cache.txt`):

| Execução | input | output | thoughts (details) | cache_read | requests | custo (RequestUsage.cost) |
|---|---|---|---|---|---|---|
| não-stream | 48 | 382 | 369 | 0 | 1 | 0.0014685 USD |
| stream | 48 | 440 | 427 | 0 | 1 | — |
| cache, 1ª | 7876 | 69 | 66 | 0 | 1 | — |
| cache, 2ª | 7876 | 3 | ausente | 4079 | 1 | — |

Conta que prova a soma: não-stream `382 = 13 candidates + 369 thoughts`.

Conta que prova o preço: `48 × 0,75/M + 382 × 3,75/M = 0,0014685 USD`, igual ao `RequestUsage.cost`. O `genai-prices` cobra thinking pela tarifa de output, e `output_tokens` é o número cobrável.

Recusa pré-chamada:

```
limite baixo: recusou antes de gerar -> The next request would exceed the input_tokens_limit of 5 (input_tokens=48).
```

Diferença de API encontrada: em 2.47, `result.usage` é propriedade, não método. `result.usage()` levanta `TypeError: 'RunUsage' object is not callable`.

---

## 6. Built-in + function declaration: PASSOU (exige flag)

Script: `spike/py/h6_builtin_mix.py`. `tools=[Tool(google_search=...), Tool(function_declarations=[ler_pdf])]`.

Sem flag, o Gemini recusa (`out/h6.txt`):

```
ClientError 400 INVALID_ARGUMENT. 'Please enable tool_config.include_server_side_tool_invocations to use Built-in tools with Function calling.'
```

Com `tool_config=ToolConfig(include_server_side_tool_invocations=True)`, os dois funcionam no mesmo request:

| Prompt | Resultado |
|---|---|
| "Qual a cotacao do dolar hoje?" | `google_search` executou. `web_search_queries=['cotacao dolar hoje real']`. Partes `tool_call` + `tool_response` na resposta. |
| "Leia o PDF anexado com id abc123..." | `function_calls=[ler_pdf(arquivo_id='abc123')]` |

Pydantic AI 2.47 liga a flag sozinho quando há built-in no Gemini 3+ (`pydantic_ai/models/google.py`, linha 869).

---

## 7. Era do cliente MCP: PASSOU (só era moderna observada)

Scripts: `spike/py/h7_mcp_server.py` (servidor `mcp` 2.2.0, `MCPServer`, Streamable HTTP em `127.0.0.1:8765/mcp`) e `spike/py/h7_mcp_client.py` (`MCPToolset`).

Critério de era: o `MCPToolset` preenche `client.initialize_result` só na sessão legada. Nulo = sessão moderna, sem `initialize`.

Saída (`out/h7.txt`, ícones cortados):

```
== local mcp 2.x ==
era da sessao: moderna (sem initialize, stateless)
server_info: name='spike-local' version=''
tools (2): ['eco', 'somar']
call ('somar', {'a': 2, 'b': 3}) -> 5
== GitHub remoto ==
era da sessao: moderna (sem initialize, stateless)
server_info: name='github-mcp-server' title='GitHub MCP Server' version='github-mcp-server/remote-7835a23...'
tools (45): ['add_comment_to_pending_review', 'add_issue_comment', ..., 'search_repositories', ..., 'update_pull_request_branch']
```

GitHub conectou com `headers={"Authorization": "Bearer $GITHUB_PAT"}`.

Limite do teste: os dois servidores negociaram a era moderna. O caminho legado do `MCPToolset` existe no código, mas não foi exercitado por falta de um servidor só-legado.

Diferença de API: em `mcp` 2.x, `FastMCP` virou `mcp.server.mcpserver.MCPServer`. Importar `mcp.server.fastmcp` levanta `ModuleNotFoundError` com link para o guia de migração.

---

## 8. FastAPI-Users: PASSOU

Script: `spike/py/h8_auth.py`. FastAPI 0.141.1, FastAPI-Users 15.0.5, SQLAlchemy 2.0.54 async, asyncpg 0.31.0, Postgres 17 em `127.0.0.1:5433`. `asyncpg` não vem com `fastapi-users[sqlalchemy]`. Foi adicionado à parte.

Saída (`out/h8.txt`):

```
--- POST /auth/register
{"id":"cca8e213-...","email":"toneli@example.com","is_active":true,"is_superuser":false,"is_verified":false}
--- POST /auth/jwt/login
{"access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer"}
--- GET /users/me (com JWT)
{"id":"cca8e213-...","email":"toneli@example.com","is_active":true,...}
--- GET /users/me (sem JWT)
HTTP 401
--- linha no Postgres
       email        | is_active
 toneli@example.com | t
```

Nenhum warning de deprecação no log do uvicorn.

---

## 9. Jev em português: PASSOU

Script: `spike/py/h9_jev_ptbr.py`. Modelo `jev-1.13.0`. Choice com 4 opções, cada uma com descrição curta em pt. State: `mensagem_do_usuario` + `anexos_na_mensagem`.

Saída (`out/h9.txt`):

| # | Frase | Anexo | Esperado | Escolha | confidence | web_search | web_fetch | ler_pdf | nenhuma |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Qual foi o resultado do jogo do Flamengo ontem? | — | web_search | web_search | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| 2 | Quanto está o dólar hoje? | — | web_search | web_search | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| 3 | Quais as novidades do Python 3.15 que saíram essa semana? | — | web_search | web_search | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| 4 | Resume pra mim esse artigo: https://pt.wikipedia.org/wiki/Cabo_Frio | — | web_fetch | web_fetch | 0.99 | 0.00 | 0.99 | 0.00 | 0.01 |
| 5 | O que diz a página https://docs.python.org/3/whatsnew/3.14.html sobre o GIL? | — | web_fetch | web_fetch | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 |
| 6 | Me faz um resumo desse contrato que eu te mandei. | contrato_locacao.pdf | ler_pdf | ler_pdf | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 |
| 7 | Qual o valor total da nota fiscal em anexo? | nf_setembro.pdf | ler_pdf | ler_pdf | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 |
| 8 | Bom dia! Tudo certo por aí? | — | nenhuma | nenhuma | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| 9 | Me explica a diferença entre lista e tupla em Python. | — | nenhuma | nenhuma | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| 10 | Resume esse PDF pra mim. | — | ambíguo (PDF sem anexo) | nenhuma | 0.38 | 0.00 | 0.00 | 0.47 | 0.53 |

Distribuição: web_search 3, web_fetch 2, ler_pdf 2, nenhuma 3.
Acerto: 9/9 nos casos não ambíguos.
Caso ambíguo: confidence 0.38, abaixo do limiar default 0.7 do ticket 11. O gate mandaria para `AUTO`.
Uso por chamada: ~450 tokens de entrada, 50 de saída.

Limite: as frases são claras e escritas por mim, não tiradas de uso real. A distribuição quase binária (1.00) mostra que o Jev entende pt-BR neste formato. Não mede frase difícil.

---

## Impacto nos tickets

Só lista. Nenhum ticket foi editado.

- **03 (scaffold)**: Python 3.14 serve; não precisa fixar 3.12. `asyncpg` entra como dependência explícita.
- **04 (auth)**: nenhum ajuste. Fluxo provado nas versões atuais.
- **06 (chat streaming)**: usar `result.usage` como propriedade. `RunUsage.output_tokens` já inclui thinking; thinking à parte em `details['thoughts_tokens']`, cache em `cache_read_tokens`. Primeiro token levou ~7 s sem thinking configurado (causa INFERIDA: thinking default do modelo).
- **07 (front)**: `shadcn init` tem de usar `-b radix` (o default Base UI quebra o `prompt-input`). Sem `baseUrl` no tsconfig (TS 6). Envolver o app com `TooltipProvider`. Bundle de 1,6 MB pede code-split se incomodar.
- **08 (crédito)**: pergunta do ADR 0004 respondida. Usage é cumulativo em todo chunk: gravar o último, nunca somar. Thinking fora de `candidates`: output cobrado = candidates + thoughts. Se usar `RunUsage.output_tokens`, não somar `thoughts_tokens` de novo. `count_tokens_before_request` funciona e serve para a reserva, ao custo de uma chamada `countTokens` extra por request.
- **10 (tools nativas)**: se um dia oferecer `google_search` built-in junto das tools nossas, o request exige `include_server_side_tool_invocations`. Pydantic AI já liga.
- **11 (roteador Jev)**: pré-requisito fechado. O aceite "os 10 casos passam" precisa dizer o que o caso 10 (ambíguo) espera: confidence abaixo do limiar, não uma tool. As descrições das opções e o campo de anexos no state entraram no teste e devem ir para o módulo.
- **17 (MCP)**: `MCPToolset` confirmado para GitHub remoto e servidor `mcp` 2.x local. Só a era moderna foi exercitada. O servidor de demo em `deploy/mcp-demo/` usa `MCPServer`, não `FastMCP`.
