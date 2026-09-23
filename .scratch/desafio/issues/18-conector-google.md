# 18 — Conector Google Drive e Gmail

**Type:** task (HITL + AFK)
**Status:** ready-for-agent
**Blocked by:** nenhum (era 16; liberado em 23/09 para rodar em localhost, deploy só troca a URL)
**Refs:** ADR 0010. Camada 3.

**HITL (wizard):** projeto GCP, habilitar Drive e Gmail API, consent screen em Testing, client OAuth web com redirect `https://chat.toneli.dev.br/api/connectors/google/callback`, adicionar e-mail do Toneli e do CPO como test users.

**AFK:** tabela `connectors` (usuário, provedor, tokens criptografados, escopos, expira_em). Fluxo OAuth. Três tools nativas: `gmail_search`, `gmail_read`, `drive_search_read`, registradas só para quem tem conector ativo. Refresh de token. Eventos `connector_linked`, `connector_revoked`. Front: tela "Conectores" com botão conectar Google.

**Aceite:**
- [ ] Conectar, perguntar "meu último e-mail sobre X" devolve resposta com dado real do Gmail.
- [ ] "resume o arquivo Y do meu Drive" lê o arquivo.
- [ ] Token expirado é renovado sem o usuário perceber; expirado sem refresh gera mensagem clara.

**HITL concluído (23/09 ~03:00):** projeto GCP, APIs, consent screen Testing, client OAuth e test users prontos. `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env`. Redirect `http://localhost:8000/api/connectors/google/callback` testado com `code=` na volta. O redirect de produção `https://chat.toneli.dev.br/...` já está cadastrado. Só falta a parte AFK.
