# 41 — Conector Google com as libs oficiais de auth (google-auth + google-auth-oauthlib) e PKCE

**Type:** task (AFK, só api/ e docs/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ADR 0010 (cita a lib do Google, código usa httpx), `docs/DECISOES-AUTONOMAS.md` (entrada do httpx no ticket 18), `docs/MOTIVACOES.md` (seção do conector), `MANHA.md` (item "ADR 0010 vs código").

**Decisão (Toneli, 23/09):** usar as libs oficiais do Google na auth. Caminho híbrido:
- `google-auth` (`google.oauth2.credentials.Credentials`, refresh, `RefreshError`) e `google-auth-oauthlib` (`Flow`) no OAuth e no refresh.
- Gmail e Drive continuam em httpx async. Motivo (pesquisa de 23/09): `google-api-python-client` está em maintenance mode, roda sobre `google-auth-httplib2` (deprecated pelo Google: "highly discouraged", não thread-safe) e é síncrono; não existe cliente oficial async para Gmail/Drive.
- PKCE ligado (padrão do `Flow`), `code_verifier` em cookie httpOnly.
Escrever ADR 0017 revisando o 0010 com isso e os links: https://github.com/googleapis/google-api-python-client (README, maintenance mode), https://pypi.org/project/google-auth-httplib2/ (deprecated), https://github.com/googleapis/google-cloud-python/blob/main/packages/google-auth-oauthlib/google_auth_oauthlib/flow.py (PKCE).

**What to build:**
- Deps em `api/pyproject.toml`: `google-auth` explícito (já é transitivo) e `google-auth-oauthlib`. Mover `httpx` de `dev` para as deps de produção (hoje só chega transitivo). `uv lock`.
- Módulo novo `api/app/google_transporte.py` com duas pontes sobre o transporte httpx injetável (`transporte_google()`), para o mock `Google` de `tests/test_conectores.py` continuar vendo `/token`:
  - `RequestHttpx(google.auth.transport.Request)`: `__call__(url, method, body, headers, timeout)` via `httpx.Client(transport=t)`; `t=None` usa o real. Usado em `creds.refresh`.
  - `AdaptadorRequests(requests.adapters.BaseAdapter)`: montado em `flow.oauth2session` quando `t` não é None.
  - `httpx.MockTransport` atende sync e async; confirme.
- `_token`: montar `Credentials(token, refresh_token, token_uri=TOKEN_URL, client_id, client_secret, scopes, expiry)`. `expiry` naive em UTC (exigência do google-auth). Se `creds.expired`, `await asyncio.to_thread(creds.refresh, RequestHttpx(t))`. Persistir `creds.token`, `creds.expiry`, refresh antigo se não vier novo. `RefreshError` → `connector_refresh_failed` com payload `{erro: str(e)[:200]}` → `ConectorExpirado(EXPIROU)`. Remover `_pedir_token` e `_expira` se ficarem sem uso.
- `authorize`: `Flow.from_client_config(...)`, `authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true", state=<JWT atual>)`. Cookie `tess_google_pkce` = `flow.code_verifier`: httpOnly, SameSite=Lax, Secure quando `ENV=prod`, `max_age=600`, `path=/api/connectors/google/callback`, setado na resposta JSON `{"url"}`.
- `callback`: sem cookie → redirect `?erro=pkce_ausente` sem chamar o Google. Recria o Flow com o `code_verifier`, `await asyncio.to_thread(flow.fetch_token, code=code)`; erro → `?erro=troca_falhou`. Usa `flow.credentials` (token, refresh_token, expiry, `granted_scopes`) no upsert. Apaga o cookie. Resto do callback igual (state JWT, `_conta`, auditoria `connector_linked`, redirects).
- `revoke` continua POST httpx manual (a lib não tem helper).
- Não mexer: tools de Gmail/Drive, `gmail_send`, `enviar_rascunho`, `_mime`, `traduzir_erro_gmail`, `_conta`, `_cifrar`/`_decifrar` (`app/mcp.py` importa) e o formato do JSON cifrado (tokens antigos seguem válidos sem reconectar).
- Se o front (`web/`) mostra os erros `?erro=`, verificar se `pkce_ausente` precisa de texto; se precisar, só a string, sem refatorar.
- `REVISAR(human)` em `_token` e no par cookie/PKCE do callback.
- Atualizar `docs/DECISOES-AUTONOMAS.md` (entrada do httpx: resolvida pelo ADR 0017) e `docs/MOTIVACOES.md`.

**Aceite:**
- [ ] Os testes existentes de `test_conectores.py`, `test_email.py` e `test_mcp.py` passam, com ajuste mínimo (só onde o formato mudou de verdade, ex.: payload de `connector_refresh_failed`).
- [ ] Teste: URL do authorize tem `code_challenge` e `code_challenge_method=S256`, e a resposta seta o cookie.
- [ ] Teste: o POST `/token` do callback leva `code_verifier` cujo S256 bate com o `code_challenge` enviado.
- [ ] Teste: callback sem cookie redireciona `?erro=pkce_ausente` e o mock não recebe request.
- [ ] Teste: refresh com `invalid_grant` gera `connector_refresh_failed` e a tool devolve o texto de "expirou".
- [ ] ADR 0017 escrito.
- [ ] Chamadas reais: Gemini 0, Google 0.

## Answer
Auth do Google agora usa `Flow` (google-auth-oauthlib) e `Credentials` (google-auth), com PKCE: `code_verifier` no cookie httpOnly `tess_google_pkce`, callback sem cookie volta `?erro=pkce_ausente` sem chamar o Google. Gmail, Drive e revoke seguem em httpx. `app/google_transporte.py` tem `RequestHttpx` e `AdaptadorRequests`: o mesmo `MockTransport` vê o `/token` do refresh e do callback. ADR 0017 escrito; 0010 aponta para ele.
Ressalvas: `OAUTHLIB_RELAX_TOKEN_SCOPE=1` no processo (sem ele, escopo parcial ou extra quebra a troca; `test_email` com escopo só de leitura pegou isso). `creds.expired` renova 3m45s antes (era 60 s). Falha de rede no refresh também vira "expirou", como no 18. Payload de `connector_refresh_failed` troca `status` por `erro`.
`test_mcp::test_erro_da_tool_mcp_volta_ao_modelo_que_tenta_de_novo` falhou 1 vez em 5 execuções, passou nas outras e no baseline: intermitente, sem relação com o Google.
REVISAR(human): `_token`, `autorizar` (state + PKCE) e `_trocar` (par cookie/PKCE do callback).
