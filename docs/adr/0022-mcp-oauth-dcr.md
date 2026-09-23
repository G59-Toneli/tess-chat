# ADR 0022 — Servidor MCP por OAuth: descoberta, DCR e PKCE feitos à mão

**Status:** aceito, 2026-09-23. Complementa o [ADR 0009](0009-registro-unico-de-tools-e-mcp-client.md). Espelha o desenho do [ADR 0017](0017-auth-google-com-libs-oficiais-e-pkce.md).

## Contexto
O cadastro de Servidor MCP pedia URL e um header `Authorization` fixo. Servidores só-OAuth (Notion, Sentry) ficavam de fora. O "Custom MCP" da Tess (docs.tess.im/en/mcp-custom.md) pede só a URL: descobre o OAuth, abre o consentimento e guarda o token por Usuário. Sem credencial válida, o servidor sai do turno. O Toneli pediu a mesma paridade em 23/09, com atalhos para Notion e Stripe. Os dois têm `registration_endpoint`.

## Decisão
1. **Dois requests, estado fora da memória.** `POST /api/mcp-servers/oauth/iniciar` e `GET /api/mcp-servers/oauth/callback`. O state é um JWT com `sub` (Usuário), `sid` (servidor) e 10 min. O `code_verifier` fica no cookie `tess_mcp_pkce`: httpOnly, SameSite=Lax, `path` só do callback. O callback sempre apaga o cookie.
2. **Descoberta pela spec MCP.** Um `initialize` sem token espera 401 com `WWW-Authenticate`. Depois vem o metadata do recurso (RFC 9728) e o do authorization server (RFC 8414, com os fallbacks OIDC). As URLs candidatas saem dos helpers do SDK `mcp` (`mcp.client.auth.utils`). O parse usa os modelos de `mcp.shared.auth`. O PKCE usa `PKCEParameters.generate()`.
3. **Só DCR (RFC 7591), cliente público.** O registro pede `token_endpoint_auth_method=none` e `grant_types=[authorization_code, refresh_token]`. Servidor sem `registration_endpoint` recebe 422: "Esse servidor exige app registrado. Use token no header."
4. **`resource` (RFC 8707)** vai no authorize, na troca e no refresh, com a URL canônica do servidor.
5. **SSRF.** Toda URL que vem de metadata passa por `validar_url` antes do request: metadata do recurso, authorization server, registration, authorize e token. Sem isso, um servidor público podia apontar o metadata para a rede interna.
6. **O Bearer mora em `headers`.** Depois do callback e de cada refresh, `headers` recebe `Authorization: Bearer <access>`, cifrado. `_cliente`, `toolset` e `tem_auth` não mudaram. A coluna nova `oauth` guarda o resto, cifrado: `client_id`, `token_endpoint`, `refresh_token`, `expires_at`, `scope`, `resource`.
7. **Estado do servidor.** `ok`, `aguardando_oauth` ou `expirado`. Antes do turno, `renovar` troca o token que vence em menos de 60 s. Refresh que falha grava `expirado`. Servidor fora de `ok` sai do turno (fail-closed) e o card mostra "Reconectar".

### Alternativas descartadas
- **`OAuthClientProvider` do SDK.** Roda o fluxo inteiro numa coroutine que espera o callback. Num web app isso exige `{state: Future}` em memória. É opaco e morre num restart.
- **App registrado por provedor (HubSpot, Slack, GitHub).** Cada provedor pede cadastro manual, segredo no `.env` e redirect por ambiente. O header fixo continua cobrindo esses casos.
- **`code_verifier` no banco.** Mesma razão do ADR 0017: o cookie vence sozinho.
- **Client ID Metadata Document.** Mais novo na spec e ainda pouco suportado. Notion e Stripe aceitam DCR.

## Consequências
- Conectar exige o mesmo browser do começo ao fim, em até 10 min.
- Cada iniciar faz um DCR novo. O provedor acumula clientes registrados. Revogação no provedor fica fora do escopo.
- O refresh roda antes da sonda do turno, em paralelo por servidor, numa sessão própria.
- A barreira de SSRF resolve o DNS de novo em cada request. DNS rebinding continua não coberto (ressalva do ticket 23).
