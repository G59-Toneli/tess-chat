# ADR 0010 — Conector Google Drive e Gmail por OAuth direto, não por MCP sidecar

**Status:** aceito, 2026-09-23. Revisado pelos ADRs [0013](0013-envio-de-email-com-confirmacao.md) (envio de e-mail), [0015](0015-pdf-do-drive-como-arquivo.md) (PDF do Drive) e [0017](0017-auth-google-com-libs-oficiais-e-pkce.md) (biblioteca). A decisão central, Conector por OAuth direto e não MCP sidecar, fica.

## Contexto
MCP oficial do Google é Developer Preview com programa fechado. App em modo Testing só autoriza test users listados. Token expira em 7 dias.

## Decisão
`google-api-python-client` com OAuth2 web flow. Token por Usuário no Postgres. Três Tools nativas somente leitura: buscar e-mails, ler e-mail, buscar e ler arquivo do Drive. Escopos `gmail.readonly` e `drive.readonly`. E-mails dos testadores cadastrados como test users. Demo em vídeo como garantia.

Conector e MCP são conceitos distintos. Conector é credencial mais tools nossas. MCP é provedor externo de tools. Implementamos os dois.

## Consequências
- Camada 3, última no plano. Não segura a Camada 1.
- Opcional se sobrar tempo: expor essas tools como servidor MCP próprio.
