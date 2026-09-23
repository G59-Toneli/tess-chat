# 01 — Spike: derrubar os INFERIDOs da arquitetura

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** —
**Refs:** ADR 0001, 0002, 0004, 0009. `research/01`, `research/02`, `research/03`.

**What to build:** um projeto descartável em `spike/` que prova ou derruba cada hipótese abaixo. Nada daqui vai para produção. Saída: `spike/RESULTADO.md` com uma seção por hipótese, veredito PASSOU/FALHOU/PARCIAL, evidência (output real, versão instalada) e o fallback recomendado quando falhou. Não decidir arquitetura: se algo falhar, registrar o fallback listado e parar.

**Hipóteses:**

1. **Resolução de dependências Python.** `uv add pydantic-ai fastapi-users[sqlalchemy] mcp>=2 google-genai typesafe-sdk` resolve sem conflito de pin. Se Pydantic AI pina `mcp<2`, registrar a versão pinada e qual era ela suporta.
2. **VercelAIAdapter → useChat.** Um endpoint FastAPI com `VercelAIAdapter(sdk_version=7)` streama para um `useChat` de `@ai-sdk/react` (ai 7.x) num Vite mínimo. Texto aparece token a token no browser.
3. **AI Elements em Vite.** `npx ai-elements@latest add conversation message prompt-input` instala e renderiza num projeto Vite + shadcn. Fallback: shadcn puro + useChat.
4. **usage_metadata no streaming do Gemini.** Com `google-genai` direto e `generate_content_stream`, em `gemini-3.8-flash` com thinking ligado: em quais chunks `usage_metadata` aparece? `thoughts_token_count` está somado dentro de `candidates_token_count` ou separado? Comparar com a resposta não-stream do mesmo prompt. Registrar os números brutos.
5. **Pydantic AI RunUsage com Google.** O `RunUsage` do Pydantic AI expõe tokens de thinking e cache separados para o provedor Google? `UsageLimits(count_tokens_before_request=True)` funciona com Google?
6. **Built-ins + function declarations.** `gemini-3.8-flash` aceita `google_search` built-in e uma function declaration nossa no mesmo request? Só registrar. ADR 0009 já decidiu por tools próprias, mas o resultado afeta se podemos oferecer o built-in como tool extra.
7. **Era do cliente MCP.** Pydantic AI `MCPToolset` conecta em `https://api.githubcopilot.com/mcp/` (servidor dual-era, precisa de PAT) e em um servidor mínimo local feito com `mcp` 2.x em Streamable HTTP? Listar tools de ambos.
8. **FastAPI-Users.** Registra, loga e devolve JWT com SQLAlchemy async + Postgres local (compose). Sem briga de versão com o FastAPI atual.
9. **Jev em português.** 10 frases reais em pt-BR, tipo Choice com 4 tools (`web_search`, `web_fetch`, `ler_pdf`, `nenhuma`). Registrar distribuição e confidence de cada uma. Este item também fecha o pré-requisito do ticket 11.

**Ambiente:** Postgres via `docker compose` em `spike/`. Chaves em `.env` (GEMINI_API_KEY, TYPESAFE_API_KEY, GITHUB_PAT opcional). Se uma chave faltar, marcar a hipótese como BLOQUEADA e seguir.

**Aceite:**
- [ ] `spike/RESULTADO.md` existe com as 9 seções e veredito em cada.
- [ ] Cada veredito tem evidência colada (output, versão).
- [ ] Hipóteses 4 e 5 trazem tabela com os números de tokens brutos.
- [ ] Nenhum arquivo fora de `spike/` foi alterado.

## Answer
9/9 PASSOU. Detalhe em `spike/RESULTADO.md`. Ajustes propagados para 03, 06, 07, 08, 11, 17.
