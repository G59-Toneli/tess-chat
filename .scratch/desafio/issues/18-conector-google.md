# 18 — Conector Google Drive e Gmail

**Type:** task (HITL + AFK)
**Status:** resolved
**Blocked by:** nenhum (era 16; liberado em 23/09 para rodar em localhost, deploy só troca a URL)
**Refs:** ADR 0010. Camada 3.

**HITL (wizard):** projeto GCP, habilitar Drive e Gmail API, consent screen em Testing, client OAuth web com redirect `https://chat.toneli.dev.br/api/connectors/google/callback`, adicionar e-mail do Toneli e dos testadores como test users.

**AFK:** tabela `connectors` (usuário, provedor, tokens criptografados, escopos, expira_em). Fluxo OAuth. Três tools nativas: `gmail_search`, `gmail_read`, `drive_search_read`, registradas só para quem tem conector ativo. Refresh de token. Eventos `connector_linked`, `connector_revoked`. Front: tela "Conectores" com botão conectar Google.

**Aceite:**
- [ ] Conectar, perguntar "meu último e-mail sobre X" devolve resposta com dado real do Gmail.
- [ ] "resume o arquivo Y do meu Drive" lê o arquivo.
- [ ] Token expirado é renovado sem o usuário perceber; expirado sem refresh gera mensagem clara.

**HITL concluído (23/09 ~03:00):** projeto GCP, APIs, consent screen Testing, client OAuth e test users prontos. `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env`. Redirect `http://localhost:8000/api/connectors/google/callback` testado com `code=` na volta. O redirect de produção `https://chat.toneli.dev.br/...` já está cadastrado. Só falta a parte AFK.

## Answer
Tabela `connectors` (migração 0012) com tokens cifrados em Fernet, OAuth web flow em `/api/connectors/google/*` com `state` JWT assinado, e três Tools de origem `google` que só entram no registro da Conversa quando o dono tem Conector. Refresh 60 s antes de vencer; sem refresh válido, a tool devolve "expirou, reconecte em Conectores". Eventos `connector_linked`, `connector_revoked`, `connector_refreshed`, `connector_refresh_failed`. Tela `/conectores` com conectar, escopos, status do token e desconectar.
Ressalvas: aceites 1 e 2 testados com Google mockado. A validação real depende do login do Toneli e está no MANHA.md. Aceite 3 provado com mock. Usa `httpx` no lugar de `google-api-python-client` (DECISOES-AUTONOMAS). PDF do Drive não é lido.
`REVISAR(human)`: `_token` (refresh), `autorizar` (state), `drive_search_read` (qual arquivo ler) em `api/app/conectores.py`, e o filtro em `estado_da_conversa`.
