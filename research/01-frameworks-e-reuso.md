# 01 — Frameworks e reuso para o chat do desafio

Pesquisa feita em 2026-09-22. Prazo do desafio: 29/09/2026. Fontes primárias: docs oficiais, GitHub e PyPI.
Regra: item sem fonte verificada está marcado **INFERIDO**.

---

## 1. Frameworks Python de agente

### 1.1 Versão atual

Datas tiradas de `api.github.com/repos/<owner>/<repo>/releases/latest` (campo `published_at`).

| Framework | Versão | Última release | Fonte |
|---|---|---|---|
| Pydantic AI | 2.47.0 | 2026-09-22 | https://api.github.com/repos/pydantic/pydantic-ai/releases/latest |
| LangGraph | 1.2.12 | 2026-09-21 | https://api.github.com/repos/langchain-ai/langgraph/releases/latest |
| Agno | 3.0.10 | 2026-09-16 | https://api.github.com/repos/agno-agi/agno/releases/latest |
| OpenAI Agents SDK | 0.22.3 | 2026-09-17 | https://api.github.com/repos/openai/openai-agents-python/releases/latest |
| Google ADK | 2.9.2 | 2026-09-18 | https://api.github.com/repos/google/adk-python/releases/latest |
| LlamaIndex | 0.14.25 | 2026-09-21 | https://api.github.com/repos/run-llama/llama_index/releases/latest |
| smolagents | 1.26.0 | 2026-05-29 | https://api.github.com/repos/huggingface/smolagents/releases/latest |

Achado: smolagents está ~4 meses sem release. Os outros seis soltaram release na última semana.

### 1.2 Recursos prontos

Legenda: ✅ nativo e documentado · 🟡 parcial ou com ressalva · ❌ não tem · (I) = INFERIDO.

| Recurso | Pydantic AI | LangGraph / LangChain 1.x | Agno | OpenAI Agents SDK | Google ADK | LlamaIndex | smolagents |
|---|---|---|---|---|---|---|---|
| Gemini + OpenAI | ✅ troca de string [1] | ✅ (I) | ✅ (I) | 🟡 Gemini só via LiteLLM / any-llm / endpoint compatível [2] | ✅ Gemini nativo; OpenAI via wrapper LiteLlm (I) | ✅ (I) | ✅ (I) |
| Tool calling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (foco em CodeAgent) |
| Cliente MCP | ✅ `MCPToolset`, stdio / Streamable HTTP / SSE [3] | ✅ `MCPAdapter` em `langchain[mcp]>=1.4.0`, sobre FastMCP [4] | ✅ `MCPTools`, stdio / Streamable HTTP [5] | ✅ (I) | ✅ `McpToolset`, stdio / Streamable HTTP [6] | 🟡 pacote de tools MCP (I) | ✅ `MCPClient` / `ToolCollection.from_mcp` [7] |
| Persistência Postgres | 🟡 serializa com `ModelMessagesTypeAdapter`; a tabela é sua [8] | ✅ `PostgresSaver` / `AsyncPostgresSaver` [9] | ✅ `PostgresDb` / `AsyncPostgresDb` [10] | ✅ `SQLAlchemySession` [11] | ✅ `DatabaseSessionService` (Postgres/MySQL/SQLite) [12] | ✅ `Memory` com `async_database_uri` Postgres [13] | ❌ (I) |
| Streaming | ✅ `run_stream`, `run_stream_events` [14] | ✅ | ✅ (I) | ✅ (I) | ✅ (I) | ✅ | 🟡 (I) |
| Contagem de uso por execução | ✅ `RunUsage` com tokens, requests e custo [14] | 🟡 (I) | 🟡 métricas (I) | ✅ (I); com Chat Completions em streaming exige `include_usage=True` [2] | 🟡 `usage_metadata` (I) | 🟡 (I) | 🟡 (I) |
| Teto de uso | 🟡 `UsageLimits` por execução: tokens, requests, tool calls, `cost_limit` em USD [14] | 🟡 `ModelCallLimitMiddleware` conta chamadas por thread/run, não tokens [15] | ❌ (I) | ❌ (I) | ❌ (I) | ❌ (I) | ❌ (I) |
| Compactação de histórico | ✅ `ProcessHistory` + exemplo de compactar por `ctx.context_window_used` [8] | ✅ `SummarizationMiddleware` com gatilho por tokens/mensagens/fração [15] | ✅ `enable_session_summaries` [16] | 🟡 `OpenAIResponsesCompactionSession` só na Responses API: **não serve com Gemini** [11] | ✅ `EventsCompactionConfig` com `token_threshold` [17] | 🟡 flush para memória longa; o buffer com resumo está depreciado [13] | ❌ (I) |
| Built-in search/fetch do provedor | ✅ `WebSearchTool` + `WebFetchTool` no Gemini [18] | (I) | (I) | 🟡 search hospedado só OpenAI (I) | ✅ google_search nativo (I) | (I) | (I) |
| Adapter para UI pronta | ✅ `VercelAIAdapter` fala o protocolo do AI SDK v5/v6/v7 [19] | 🟡 via assistant-ui [20] | 🟡 AgentOS (I) | ❌ (I) | 🟡 via assistant-ui [20] | ❌ (I) | ❌ (I) |

**Ponto crítico: teto por usuário.** Nenhum framework Python tem orçamento persistente por usuário. `UsageLimits` e os middlewares valem por execução ou por thread. Na rota Python o ledger de tokens por usuário é código seu: soma `RunUsage` numa tabela e bloqueia antes de chamar o modelo.

**Ponto forte do Pydantic AI com Gemini.** `WebSearchTool` e `WebFetchTool` rodam no provedor Google. Isso cobre busca web e scraping sem chave de API externa [18]. Ressalva documentada: com Google, o `WebSearchTool` não gera partes de mensagem em streaming. As fontes podem não aparecer ao vivo na UI [18].

**PDF e imagem no Pydantic AI.** `ImageUrl`, `DocumentUrl` e `BinaryContent` com `media_type='application/pdf'`. O Google aceita todos os tipos de URL [21].

---

## 2. UIs de chat full-stack prontas

| Projeto | Licença | Stack | Share público | Teto de crédito | Auditoria | Compactação | MCP | Customizar backend |
|---|---|---|---|---|---|---|---|---|
| **LibreChat** v0.8.8-rc3 (data INFERIDA) | MIT [22] | Node + React + MongoDB [22] | ✅ link read-only; público sem login com `ALLOW_SHARED_LINKS_PUBLIC=true` [23] | ✅ `balance`: `startBalance`, refill; bloqueia pelo custo do prompt, é leniente com completion [24] | 🟡 `AuditLog` só grava grant/revoke de permissão; o resto é log Winston em arquivo [25] | ✅ automática ao estourar contexto, gatilho configurável [26] | ✅ [22] | Difícil: base grande, Node/Mongo |
| **Open WebUI** | BSD-3 + cláusula de marca desde v0.6.6; remover marca só com ≤50 usuários / 30 dias [27] | Python + Svelte; SQLite ou Postgres [28] | 🟡 share de chat existe (I); README cita "Channels", que não é link público [28] | ❌ nativo; issue aberta, só plugin de terceiros (owui-quota) [29] | 🟡 `AUDIT_LOG_LEVEL` grava requests em arquivo [30] | ✅ desligada por padrão, limiar default 80000 tokens [31] | ✅ MCP / MCPO / OpenAPI [28] | Médio: Python, mas é monólito grande |
| **Lobe Chat (LobeHub)** | LobeHub Community License, não é OSI [32] | Next.js + Postgres (I) | (I) | (I) | (I) | (I) | ✅ [32] | Difícil; licença restritiva |
| **HF chat-ui** | Apache-2.0 [33] | SvelteKit + MongoDB [33] | ✅ [33] | ❌ (I) | ❌ (I) | ❌ (I) | ✅ [33] | Só fala API compatível com OpenAI [33] |
| **Chainlit** | Apache-2.0 [34] | Python | (I) | ❌ | ❌ | ❌ | (I) | Fácil em Python; **mantido pela comunidade desde 01/05/2025** [34] |
| **assistant-ui** | MIT [20] | Biblioteca React, não é app | ❌ | ❌ | ❌ | ❌ | — | Backend é seu; aceita AI SDK, LangGraph, ADK, data-stream custom [20]. Persistência de thread pronta só no Assistant Cloud pago [20] |
| **Vercel Chatbot** (template) | Apache-2.0 [35] | Next.js + AI SDK + Drizzle + Postgres + Auth.js [36] | ✅ chat público/privado [36]; acesso sem login (I) | 🟡 "entitlements" por usuário [36]; conta mensagens por dia, não tokens (I) | ❌ (I) | ❌ (I) | ❌ (I) | Fácil em TS. Depende de Vercel Blob e AI Gateway: no VPS troca Blob por disco/S3 e Gateway por `@ai-sdk/google` (I) |

Leitura cética:
- LibreChat cobre mais itens do checklist sem código. Falta auditoria completa de eventos.
- Risco de avaliação: entregar LibreChat quase sem mudança pode ser lido como "não construiu". **INFERIDO**, depende do avaliador.
- Open WebUI tem compactação e auditoria em arquivo. Falta teto de crédito. A cláusula de marca é irrelevante para ≤50 usuários.

---

## 3. Rota TypeScript: Vercel AI SDK + Next.js

Versão atual do pacote `ai`: **7.0.111**, publicada em 2026-09-22 [37][38].

| Requisito | Cobertura | Fonte |
|---|---|---|
| Cliente MCP | ✅ `createMCPClient` em `@ai-sdk/mcp`; HTTP recomendado em produção, SSE, stdio só local. MCP Prompts é experimental | [39] |
| Gemini | ✅ `@ai-sdk/google` | [40] |
| PDF | ✅ "The Google provider supports file inputs, e.g. PDF files" | [40] |
| Imagem | ✅ | [40] |
| Busca e scraping pelo provedor | ✅ tool `google_search` e tool URL context (até 20 URLs) | [40] |
| Uso de tokens | ✅ usage + `providerMetadata` com tokens em cache e de raciocínio | [40] |
| Compactação | 🟡 helper `pruneMessages` + `prepareStep`; resumo por LLM é receita do cookbook, você implementa | [41][42] |
| Componentes de UI | ✅ AI Elements sobre shadcn/ui: conversation, message, prompt-input com anexos, sources, reasoning, tool | [43] |

Esforço comparado:
- **TS puro** (template Vercel Chatbot): histórico, auth, share e anexos já vêm prontos. Falta ledger de tokens, compactação por resumo, auditoria e adaptação ao VPS.
- **Python + frontend AI SDK**: o `VercelAIAdapter` do Pydantic AI aceita `sdk_version=7` e emite o mesmo protocolo da v6 [44]. O front usa `useChat` + AI Elements; o backend FastAPI faz o resto. Custo extra: duas linguagens e dois deploys.
- O protocolo de stream exige o header `x-vercel-ai-ui-message-stream: v1` e é documentado para backend em Python [45].

---

## 4. Libs para as partes difíceis

### 4.1 Scraping para LLM

| Opção | Tipo | Free tier / licença | Ressalva | Fonte |
|---|---|---|---|---|
| Gemini URL context / `WebFetchTool` | Tool do provedor | Sem chave extra | Limite de 20 URLs e 34MB por URL | [18][40] |
| Jina Reader (`r.jina.ai/<url>`) | API | 20 RPM sem chave; 500 RPM com chave grátis | Paga por token depois do crédito inicial | [46] |
| Firecrawl | API | 1.000 créditos/mês, sem cartão; 10 scrapes/min | 1 crédito = 1 página | [47] |
| Crawl4AI 0.9.3 | Lib local | Apache-2.0 | Exige Playwright + Chromium no VPS; em ARM (Oracle Ampere) funciona (I) | [48] |
| trafilatura | Lib local | Apache-2.0 desde v1.8.0 | Não renderiza JavaScript (I); leve | [49] |

### 4.2 Busca web

| API | Free tier | Cartão | Fonte |
|---|---|---|---|
| Tavily | 1.000 créditos/mês | Não | [50] |
| Serper | 2.500 queries grátis | Não | [51] |
| Exa | US$ 20 iniciais + US$ 10/mês; busca a US$ 7 / 1.000 | (I) | [52] |
| Brave | US$ 5/mês em crédito; US$ 5 / 1.000 | **Sim**, antifraude | [53] |
| Gemini `google_search` | Incluído na chamada do modelo; preço de grounding está no relatório de modelos (I) | — | [40] |

### 4.3 PDF

| Opção | Licença / limite | Ressalva | Fonte |
|---|---|---|---|
| PDF nativo no Gemini | Até 50MB ou 1.000 páginas; ~258 tokens por página | Entende layout, tabela e imagem. Arquivo grande ou multi-turno: usar Files API | [54] |
| pypdf | BSD (I) | Só texto; perde tabela e imagem | (I) |
| PyMuPDF / pymupdf4llm | **AGPL v3** ou licença comercial Artifex | AGPL num serviço web exige abrir o código. Aceitável num desafio público; risco em produto | [55] |

Recomendação para o desafio: mandar o PDF direto ao Gemini. Fallback para modelo sem PDF nativo: pypdf.

---

## 5. Projetos que já fazem compactação e teto por usuário

| Projeto | Compactação | Teto por usuário | Como reusar | Fonte |
|---|---|---|---|---|
| LibreChat | ✅ automática, gatilhos `token_ratio` / `remaining_tokens` / `messages_to_refine`, `reserveRatio` 5% | ✅ `balance` em créditos (1000 créditos = US$ 0,001) | Usar o app inteiro, ou ler o código como referência | [24][26] |
| Open WebUI | ✅ limiar 80k, `/compact` manual, corte sempre numa mensagem do usuário | ❌ nativo; plugin owui-quota | Referência de design da compactação | [29][31] |
| LiteLLM Proxy | ❌ | ✅ `max_budget` em USD por usuário/key/time, `budget_duration`, rejeita ao estourar, exige Postgres | Colocar o proxy entre app e provedor | [56] |
| LangChain `SummarizationMiddleware` | ✅ | — | Middleware no agente LangChain 1.x | [15] |
| Pydantic AI `ProcessHistory` | ✅ exemplo pronto de compactar perto do limite | 🟡 por execução | Copiar o exemplo da doc | [8] |

**Alerta LiteLLM.** Em 24/03/2026 as versões 1.82.7 e 1.82.8 no PyPI saíram com malware que roubava credenciais. Foram removidas [57][58]. Se usar: fixar versão e conferir hash.

---

## Recomendação

### Rota A — Python próprio: FastAPI + Pydantic AI + Postgres + front AI SDK/AI Elements

O que vem pronto:
- Gemini e OpenAI por troca de string.
- Busca e scraping via `WebSearchTool` + `WebFetchTool` do Gemini, sem chave externa.
- PDF e imagem com `BinaryContent`.
- Cliente MCP com `MCPToolset`.
- Compactação com `ProcessHistory`, a partir do exemplo da doc.
- Streaming para `useChat` com `VercelAIAdapter(sdk_version=7)`.

O que você escreve:
- Tabelas de usuário, conversa, mensagem, settings e tools.
- Ledger de tokens por usuário que soma `RunUsage` e bloqueia antes da chamada.
- Tabela de auditoria append-only.
- Link público read-only.
- Auth.

Trade-off: mais código, mas é todo seu e defensável na avaliação. Duas linguagens no deploy. Estimativa: 1,5 a 2 dias (INFERIDO).
Variante TS: começar do template Vercel Chatbot. Ganha auth, histórico e share prontos. Perde o `ProcessHistory`: compactação e ledger ficam por sua conta. No VPS precisa trocar Blob e AI Gateway.

### Rota B — Fork do LibreChat

O que vem pronto: multi-conversa, share público, créditos com teto, compactação automática, MCP, busca web, arquivos e imagem, multi-provedor. Tudo documentado [22][23][24][26].
O que falta: auditoria completa de eventos. Isso é código novo dentro do backend Node/Express + MongoDB.
Trade-off:
- Entrega mais rápida do checklist (INFERIDO: <1 dia até o deploy).
- Base de código grande, em Node e Mongo, fora da preferência Python.
- Risco de a avaliação ler como "instalou um app pronto" (INFERIDO).
- O requisito "persistência em banco" é atendido em MongoDB, não em SQL.

**Minha escolha: Rota A.** Todos os requisitos centrais têm peça pronta e documentada. As lacunas (ledger, auditoria, share) são CRUD simples. A Rota B vira plano de contingência se no dia 27/09 a Rota A não estiver de pé.

---

## Fontes

1. https://pypi.org/project/pydantic-ai/
2. https://openai.github.io/openai-agents-python/models/
3. https://pydantic.dev/docs/ai/mcp/client/
4. https://docs.langchain.com/oss/python/langchain/mcp
5. https://docs.agno.com/tools/mcp/overview
6. https://adk.dev/tools-custom/mcp-tools/
7. https://huggingface.co/docs/smolagents/tutorials/tools
8. https://pydantic.dev/docs/ai/core-concepts/message-history/
9. https://docs.langchain.com/oss/python/langgraph/persistence
10. https://docs.agno.com/database/overview
11. https://openai.github.io/openai-agents-python/sessions/
12. https://adk.dev/sessions/session/
13. https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/
14. https://pydantic.dev/docs/ai/core-concepts/agent/
15. https://docs.langchain.com/oss/python/langchain/middleware/built-in
16. https://docs.agno.com/sessions/session-summaries
17. https://adk.dev/context/compaction/
18. https://pydantic.dev/docs/ai/tools-toolsets/builtin-tools/
19. https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/
20. https://github.com/assistant-ui/assistant-ui
21. https://pydantic.dev/docs/ai/core-concepts/input/
22. https://github.com/danny-avila/LibreChat
23. https://www.librechat.ai/docs/features/shareable_links
24. https://www.librechat.ai/docs/configuration/token_usage
25. https://github.com/danny-avila/LibreChat/pull/13087
26. https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/summarization
27. https://docs.openwebui.com/license/
28. https://github.com/open-webui/open-webui
29. https://github.com/open-webui/open-webui/issues/23323 · https://github.com/xyonium/owui-quota
30. https://docs.openwebui.com/reference/env-configuration/
31. https://docs.openwebui.com/troubleshooting/context-window/
32. https://github.com/lobehub/lobe-chat
33. https://github.com/huggingface/chat-ui
34. https://github.com/Chainlit/chainlit
35. https://raw.githubusercontent.com/vercel/chatbot/main/LICENSE
36. https://github.com/vercel/chatbot
37. https://registry.npmjs.org/ai/latest
38. https://github.com/vercel/ai/releases
39. https://ai-sdk.dev/docs/ai-sdk-core/mcp-tools
40. https://ai-sdk.dev/providers/ai-sdk-providers/google
41. https://ai-sdk.dev/docs/reference/ai-sdk-ui/prune-messages
42. https://ai-sdk.dev/v7/cookbook/guides/agent-context-compaction
43. https://elements.ai-sdk.dev/
44. https://pydantic.dev/docs/ai/api/ui/vercel_ai/
45. https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
46. https://jina.ai/reader/
47. https://www.firecrawl.dev/pricing
48. https://github.com/unclecode/crawl4ai
49. https://github.com/adbar/trafilatura
50. https://www.tavily.com/pricing
51. https://serper.dev/
52. https://exa.ai/pricing
53. https://brave.com/search/api/
54. https://ai.google.dev/gemini-api/docs/document-processing
55. https://github.com/pymupdf/PyMuPDF
56. https://docs.litellm.ai/docs/proxy/users
57. https://docs.litellm.ai/blog/security-update-march-2026
58. https://futuresearch.ai/blog/litellm-pypi-supply-chain-attack/
