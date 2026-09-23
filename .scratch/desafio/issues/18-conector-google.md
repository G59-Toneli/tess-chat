# 18 — Conector Google Drive e Gmail

**Type:** task (HITL + AFK)
**Status:** blocked
**Blocked by:** 16
**Refs:** ADR 0010. Camada 3.

**HITL (wizard):** projeto GCP, habilitar Drive e Gmail API, consent screen em Testing, client OAuth web com redirect `https://<nome>.duckdns.org/api/connectors/google/callback`, adicionar e-mail do Toneli e do CPO como test users.

**AFK:** tabela `connectors` (usuário, provedor, tokens criptografados, escopos, expira_em). Fluxo OAuth. Três tools nativas: `gmail_search`, `gmail_read`, `drive_search_read`, registradas só para quem tem conector ativo. Refresh de token. Eventos `connector_linked`, `connector_revoked`. Front: tela "Conectores" com botão conectar Google.

**Aceite:**
- [ ] Conectar, perguntar "meu último e-mail sobre X" devolve resposta com dado real do Gmail.
- [ ] "resume o arquivo Y do meu Drive" lê o arquivo.
- [ ] Token expirado é renovado sem o usuário perceber; expirado sem refresh gera mensagem clara.
