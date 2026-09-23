# 29 — Conector mostra a conta Google vinculada e explica erros do Gmail

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 28
**Refs:** ADR 0010, ADR 0013, `api/app/conectores.py`, `web/src/pages/Conectores.tsx`, `web/src/components/RascunhoEmail.tsx`. Caso real do Toneli em 23/09: reconectou com uma conta Google criada a partir de um e-mail Outlook; o Gmail devolveu 400 "Mail service not enabled" e a tela só repetiu o texto cru.

**What to build:**
1. **Conta vinculada.** No callback do OAuth, chamar `https://www.googleapis.com/oauth2/v3/userinfo` (escopo `openid email` somado aos atuais; ou `https://gmail.googleapis.com/gmail/v1/users/me/profile` para o `emailAddress`) e gravar `connectors.conta_email` (migração `0017`). O evento `connector_linked` leva `conta_email`. O card em `/conectores` mostra "Conectado como fulano@gmail.com".
2. **Aviso na conexão.** Logo depois de conectar, chamar `users/me/profile` do Gmail. Se devolver 400 "Mail service not enabled" (ou 403 equivalente), gravar `connectors.gmail_disponivel = false` e o card mostra um alerta: "Esta conta Google não tem caixa Gmail (é uma conta criada com um e-mail de outro provedor). Buscar, ler e enviar e-mails não vão funcionar. Conecte uma conta @gmail.com ou Workspace com Gmail ativo." Drive continua funcionando. Tools de Gmail não são registradas para esse conector (mesma regra do escopo faltante do ticket 25).
3. **Erros do Gmail traduzidos.** Mapear no back, em um lugar só, os erros do Gmail para texto de usuário em pt-BR, com causa e ação: `Mail service not enabled` → conta sem Gmail; `insufficient authentication scopes` → reconectar para dar a permissão de envio; `invalid_grant` / token revogado → reconectar; `Recipient address required` / `Invalid To header` → destinatário inválido; quota (429) → tentar mais tarde; outro → texto genérico com o código. O card do Rascunho mostra esse texto no estado de erro, com um link "Ir para Conectores" quando a ação é reconectar. O texto cru do Google fica só no payload do evento `email_send_failed`.

**Aceite:**
- [ ] Teste: callback com userinfo mockado grava `conta_email`; `GET /api/connectors` devolve.
- [ ] Teste: `users/me/profile` mockado com 400 "Mail service not enabled" marca `gmail_disponivel=false`, não registra tools de Gmail e o card avisa.
- [ ] Teste: envio com 400 "Mail service not enabled" devolve ao front a mensagem traduzida; o evento guarda o erro cru.
- [ ] Screenshots dark: `29-conector-conta.png` (card com o e-mail), `29-conector-sem-gmail.png` (alerta), `29-rascunho-erro.png`.
- [ ] Quem já está conectado sem `conta_email`: card mostra "Reconecte para ver a conta" e nada quebra.
