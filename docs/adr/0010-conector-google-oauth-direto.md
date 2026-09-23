# ADR 0010 — Conector Google Drive e Gmail por OAuth direto, não por MCP sidecar

**Status:** aceito, 2026-09-23

## Contexto
MCP oficial do Google é Developer Preview com programa fechado. App em modo Testing só autoriza test users listados. Token expira em 7 dias.

## Decisão
`google-api-python-client` com OAuth2 web flow. Token por Usuário no Postgres. Três Tools nativas somente leitura: buscar e-mails, ler e-mail, buscar e ler arquivo do Drive. Escopos `gmail.readonly` e `drive.readonly`. E-mail do CPO cadastrado como test user. Demo em vídeo como garantia.

Conector e MCP são conceitos distintos. Conector é credencial mais tools nossas. MCP é provedor externo de tools. Implementamos os dois.

## Consequências
- Camada 3, última no plano. Não segura a Camada 1.
- Opcional se sobrar tempo: expor essas tools como servidor MCP próprio.
