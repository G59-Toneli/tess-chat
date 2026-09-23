# ADR 0009 — Registro único de Tools (nativa e MCP); cliente MCP só Streamable HTTP

**Status:** aceito, 2026-09-23

## Contexto
Requisito: "adicionar e utilizar tools", com busca e scraping. Diferencial: MCP. Auditoria exige ver cada tool call. A spec MCP atual `2026-07-28` quebrou compatibilidade com clientes legados.

## Decisão
Toda Tool passa por um registro só: origem `nativa` ou `mcp`, ativável por Conversa, auditada por chamada. `web_search` e `web_fetch` são tools nossas (Tavily mais Jina ou trafilatura), não os built-ins do Gemini. Os built-ins não passam pelo registro, não têm toggle nem evento. O usuário cadastra um Servidor MCP por URL. O app lista as tools e as expõe ao modelo como function declarations. Só Streamable HTTP: stdio num app multiusuário é executar processo arbitrário no servidor.

## Consequências
- Cliente MCP precisa ser dual-era: SDK oficial `mcp` 2.x, ou `MCPToolset` do Pydantic AI se confirmado. Ticket 01 checa a era e o conflito de pin.
- Demo com servidor remoto do GitHub (compatível confirmado) e um servidor mínimo nosso no compose como plano B.
