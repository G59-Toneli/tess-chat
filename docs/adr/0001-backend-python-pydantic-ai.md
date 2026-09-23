# ADR 0001 — Backend em Python com FastAPI e Pydantic AI

**Status:** aceito, 2026-09-23

## Contexto
Chat com tools, vision, PDF, MCP, compactação e cap de crédito, em ~2 dias. Toneli defende Python na entrevista. Pesquisa em `research/01-frameworks-e-reuso.md`.

## Opções
1. FastAPI + Pydantic AI.
2. LangGraph. Checkpointer pronto, mas API mais larga e menos tipada.
3. Fork do LibreChat (Node + Mongo). Cobre quase tudo, mas soa "instalou app pronto" e foge do Python.

## Decisão
Opção 1. Pydantic AI traz de fábrica: troca de provedor por string, tool calling tipado, cliente MCP, streaming, `RunUsage` por execução, hook `ProcessHistory` para compactação, `VercelAIAdapter` para o front. Ele fala `generateContent` com o Gemini. Não usamos a Interactions API: o histórico precisa ficar no nosso banco para a compactação própria funcionar.

## Consequências
- Ledger de crédito, auditoria, share e auth são código nosso. São CRUD.
- Framework é fino: cada peça é explicável na entrevista.
- LibreChat fica como contingência se em 27/09 nada estiver de pé.
