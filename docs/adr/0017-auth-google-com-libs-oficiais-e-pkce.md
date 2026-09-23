# ADR 0017 — Auth do Google com as libs oficiais e PKCE; Gmail e Drive seguem em httpx

**Status:** aceito, 2026-09-23. Revisa o [ADR 0010](0010-conector-google-oauth-direto.md) na biblioteca. A decisão do 0010 (Conector por OAuth direto, não MCP sidecar) fica igual.

## Contexto
O ADR 0010 cita `google-api-python-client`. O ticket 18 fez tudo em `httpx` direto: OAuth, refresh, Gmail e Drive (`docs/DECISOES-AUTONOMAS.md`, 18). O código contrariava o ADR sem ADR novo. O Toneli decidiu em 23/09 usar as libs oficiais onde elas são mantidas e servem.

Pesquisa (23/09):
- `google-api-python-client` está em maintenance mode ([README](https://github.com/googleapis/google-api-python-client)). Roda sobre `google-auth-httplib2`, e o Google marca esse pacote como deprecated, "highly discouraged", não thread-safe ([PyPI](https://pypi.org/project/google-auth-httplib2/)). É síncrono.
- Não existe cliente oficial async para Gmail nem para Drive.
- `google-auth` e `google-auth-oauthlib` são mantidos. O `Flow` liga PKCE por padrão: gera o `code_verifier` e manda `code_challenge` com S256 ([flow.py](https://github.com/googleapis/google-cloud-python/blob/main/packages/google-auth-oauthlib/google_auth_oauthlib/flow.py)).

## Decisão
1. **Auth pelas libs oficiais.** `google_auth_oauthlib.flow.Flow` monta a URL de consentimento e troca o code. `google.oauth2.credentials.Credentials` decide se o token venceu (`expired`) e renova (`refresh`). Falha de renovação é `RefreshError`: vira `connector_refresh_failed` com o erro cru no payload e o texto "expirou" para o modelo.
2. **PKCE ligado.** O `code_verifier` vai num cookie `tess_google_pkce`: httpOnly, SameSite=Lax, Secure em produção, 10 min, `path` só do callback. O callback sem cookie volta com `?erro=pkce_ausente` e não chama o Google. O callback sempre apaga o cookie. O `state` segue sendo o JWT do ticket 18: ele identifica o dono; o PKCE amarra o code ao browser que pediu.
3. **Gmail e Drive seguem em `httpx` async.** A alternativa oficial é o `google-api-python-client`, e ela cai pelos motivos da pesquisa.
4. **As libs de auth passam pelo transporte injetável.** `app/google_transporte.py` tem duas pontes sobre `httpx`: `RequestHttpx` (interface `google.auth.transport.Request`, usada no refresh) e `AdaptadorRequests` (adapter do `requests`, montado no `OAuth2Session` do `Flow`). Os testes seguem com um `httpx.MockTransport` só, que atende sync e async. As libs são síncronas: rodam em `asyncio.to_thread`.
5. **`OAUTHLIB_RELAX_TOKEN_SCOPE=1`.** Sem isso, o oauthlib levanta `Warning` quando o Google devolve escopo diferente do pedido. Isso acontece de verdade: consentimento granular (o usuário desmarca `gmail.send`) e `include_granted_scopes` (escopo antigo volta junto). O Conector grava os escopos concedidos, como antes.
6. **Revoke continua POST `httpx` manual.** A lib não tem helper de revogação.
7. **Formato do JSON cifrado igual.** Tokens gravados antes deste ADR seguem válidos sem reconectar.

### Alternativas descartadas
- **`google-api-python-client` para tudo.** Maintenance mode, httplib2 deprecated, síncrono, fora do transporte injetável.
- **Tudo em `httpx` (estado do ticket 18).** Funciona, mas reimplementa refresh e troca de code à mão e fica sem PKCE. As libs oficiais dão isso pronto.
- **Guardar o `code_verifier` no banco, indexado pelo `state`.** Pede tabela ou coluna nova e limpeza de linha vencida. O cookie vence sozinho em 10 min.
- **Capturar o `Warning` de escopo em vez da variável de ambiente.** O `Warning` sobe antes do `OAuth2Session` gravar o token, e `flow.credentials` precisa dele.

## Consequências
- Duas deps novas de produção: `google-auth` (antes transitiva) e `google-auth-oauthlib` (traz `requests-oauthlib` e `oauthlib`). `httpx` sai de `dev` para produção.
- `creds.expired` conta o token como vencido 3m45s antes do `expiry` (antes: 60 s). Renova um pouco mais cedo.
- O refresh e a troca de code rodam em thread. Custo: uma thread por refresh, raro (1 por hora por Usuário).
- `OAUTHLIB_RELAX_TOKEN_SCOPE` é variável de processo: vale para qualquer uso de oauthlib na API. Hoje só o Conector usa.
- Conectar exige o mesmo browser do começo ao fim, em até 10 min.
