# 52 — Servidor MCP por OAuth (descoberta + DCR + PKCE)

**Type:** task (api/ e web/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ADR 0009, ADR 0017, ticket 17, ticket 23. Pedido do Toneli em 23/09. Plano: `C:\Users\Admin\.claude\plans\fala-cara-atualmente-reactive-curry.md`.

**Problema:** hoje o cadastro de Servidor MCP pede URL e um header `Authorization` fixo (`api/app/mcp.py:120`). A Tess tem o "Custom MCP" (https://docs.tess.im/en/mcp-custom.md): o usuário cola só a URL, a Tess descobre o OAuth, abre o consentimento e guarda o token por usuário. Sem credencial válida o servidor some do turno (fail-closed). Queremos a mesma paridade.

**Decisão (Toneli, 23/09):** OAuth genérico para qualquer URL. Atalhos de 1 clique para Notion (`https://mcp.notion.com/mcp`) e Stripe (`https://mcp.stripe.com`). Os dois têm `registration_endpoint` (DCR). O cadastro por header continua.

## Desenho (escrever em ADR 0022)
- Dança à mão, espelhando o ADR 0017. O state é um JWT com `sub` = usuário, `sid` = servidor e validade de 10 min. O `code_verifier` fica num cookie httpOnly com `path` no callback novo. Discovery, DCR, troca e refresh usam httpx direto. O parse usa os modelos de `mcp.shared.auth` (`ProtectedResourceMetadata`, `OAuthMetadata`, `OAuthClientMetadata`, `OAuthClientInformationFull`, `OAuthToken`). Os helpers vêm de `mcp.client.auth.utils` (`extract_resource_metadata_from_www_auth`, `build_protected_resource_metadata_discovery_urls`, `build_oauth_authorization_server_metadata_discovery_urls`). Nada de reescrever parser.
- Alternativa descartada: `OAuthClientProvider` do SDK. Ele roda o fluxo inteiro numa coroutine que espera o callback. Num web app isso exige `{state: Future}` em memória, que é opaco e morre num restart.
- Só DCR. Servidor sem `registration_endpoint` (HubSpot, Slack, GitHub) recebe 422: "Esse servidor exige app registrado. Use token no header."
- `resource` (RFC 8707) vai no authorize e no token, com a URL canônica do servidor.
- **SSRF:** toda URL que vem de metadata (authorization server, registration, authorize, token) passa por `validar_url` antes do request. Sem isso o ticket 23 fica furado.

## Escopo
**Banco:** migration `0020_mcp_oauth.py`. Em `mcp_servers`:
- `oauth`: Text nulo, JSON cifrado com `_cifrar`, com `client_id`, `client_secret?`, `token_endpoint`, `refresh_token`, `expires_at`, `scope`, `resource`;
- `estado`: Text, `ok` | `aguardando_oauth` | `expirado`, default `ok`.

**Jogada cirúrgica:** depois do callback e de cada refresh, grave `headers = {"Authorization": "Bearer <access>"}` cifrado na coluna que já existe. Assim `_cliente`, `toolset` e `tem_auth` não mudam.

**`api/app/mcp_oauth.py`** (novo):
- `POST /api/mcp-servers/oauth/iniciar {nome, url, sid?}`, em 5 passos:
  1. `validar_url`.
  2. GET sem auth, esperando 401 com `WWW-Authenticate`.
  3. Descoberta: RFC 9728, depois RFC 8414 com fallbacks.
  4. DCR com `redirect_uris=[{public_base_url}/api/mcp-servers/oauth/callback]`, `grant_types=[authorization_code, refresh_token]` e `token_endpoint_auth_method=none`.
  5. Grava a linha com `estado=aguardando_oauth` e `ativo=False`, seta o cookie e devolve `{id, url}`.
  Com `sid` (reconectar), reaproveita a linha do usuário.
- `GET /api/mcp-servers/oauth/callback`, em 5 passos:
  1. Valida state e cookie.
  2. Troca o code, mandando `code_verifier` e `resource`.
  3. Grava tokens e `headers`.
  4. Conecta, lista e grava as tools. Extraia o bloco de `cadastrar` (`mcp.py:206-221`) para uma função comum.
  5. Grava `estado=ok` e `ativo=True`, e devolve 303 para `/mcp?conectado=1`.
  Falha na listagem grava `estado=expirado` e volta com `erro=`. O callback sempre apaga o cookie.
- `renovar(srv)`:
  - Se `expires_at` está a menos de 60 s, faz POST `grant_type=refresh_token` (+ `resource`). Grava o refresh_token novo se vier, senão mantém o antigo. Reescreve `headers` e audita `mcp_oauth_refreshed`.
  - Se falhar, grava `estado=expirado` e audita `mcp_oauth_refresh_failed`.
  - Usa `SessionLocal()` próprio, como `conectores.py:171`.
- Transporte injetável `transporte_mcp_oauth()`, igual a `transporte_google` (`conectores.py:111`).
- Auditoria: `mcp_oauth_started`, `mcp_oauth_linked`, `mcp_server_added` com `tem_auth`.

**Turno:** em `api/app/tools.py:~296`, chame `renovar` antes de `alcancavel` nos servidores com `oauth`. Servidor `aguardando_oauth` ou `expirado` sai do turno.

**API de saída:** `McpServerOut` ganha `estado` e `oauth: bool`.

**Front** (ler `docs/UI-GUIA.md` antes):
- `web/src/pages/Mcp.tsx` ganha:
  - o botão "Conectar por OAuth";
  - os atalhos Notion e Stripe com a URL preenchida;
  - o estado aguardando ou expirado no card, com botão "Reconectar".
- Usar redirect, não popup, igual ao conector Google.
- `web/src/lib/mcp.ts` ganha `iniciarOAuth` e o campo `estado`.
- Ao voltar com `?conectado=1` ou `?erro=`, mostrar feedback, como `/conectores` faz.

**Docs:**
- `docs/adr/0022-mcp-oauth-dcr.md`.
- Atualizar `docs/MCP-RECOMENDADOS.md:58`, que justifica só o header fixo.
- Entrada em `CONTEXT.md` se nascer termo novo.
- `REVISAR(human)` na descoberta, no DCR, na troca e no refresh.

## Aceite (testes com `httpx.MockTransport` como auth server + mcp-demo)
- `iniciar` devolve uma URL de authorize com `code_challenge`, `code_challenge_method=S256`, `resource` e o `client_id` que o DCR devolveu.
- Servidor sem `registration_endpoint` recebe 422 com a mensagem.
- Metadata apontando para um IP interno é recusado.
- O callback deixa o servidor em `ok`, `ativo`, com as tools do mcp-demo no registro.
- Callback sem cookie volta com `erro=pkce_ausente`. State adulterado volta com `erro=state_invalido`.
- Token vencido é renovado antes do turno, e o header gravado muda.
- Refresh com resposta 400 marca `expirado`, e o servidor não entra no toolset do turno.
- O cadastro por header continua passando nos testes existentes.
- Screenshot no Brave (dark, 1440x900) de `/mcp` com os atalhos e com um card expirado.

## Fora do escopo
- Popup. Revogação no provedor. Servidor compartilhado por workspace. Client ID Metadata Document.
- E2E real com Notion e Stripe: é HITL do Toneli, vai no `MANHA.md`.

## Answer
- `api/app/mcp_oauth.py`: iniciar (sonda 401, RFC 9728/8414 pelos helpers do SDK, DCR público, PKCE S256, `resource`) e callback (state JWT + cookie, troca, lista e grava tools). `renovar` roda antes da sonda do turno; falha marca `expirado` e tira o servidor do turno. Migração 0020, ADR 0022.
- `validar_url` roda em toda URL de metadata (recurso, auth server, registration, authorize, token), inclusive no refresh.
- Front: atalhos Notion/Stripe, botão "Conectar por OAuth", badge aguardando/expirado e "Reconectar" no card, toast na volta. Screenshot: `.scratch/desafio/screens/52-mcp-oauth.png`.
- Ressalvas: sonda é POST `initialize` (DECISOES-AUTONOMAS); cada iniciar faz um DCR novo; E2E real com Notion/Stripe é HITL no MANHA.md.
- `REVISAR(human)`: `_descobrir`, `_registrar`, `_pedir_token`, `renovar`, `_concluir`.
