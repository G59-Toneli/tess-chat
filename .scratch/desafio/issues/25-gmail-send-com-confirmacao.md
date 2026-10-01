# 25 — Responder e-mail pelo Gmail com confirmação do Usuário

**Type:** task (AFK + HITL)
**Status:** resolved
**Blocked by:** 18
**Refs:** ADR 0013 (novo), ADR 0010, ADR 0007. `api/app/conectores.py`, `api/app/tools.py`, `web/src/pages/Conectores.tsx`, componente de mensagem do chat.

**What to build (AFK):** tudo que o ADR 0013 fixa.
- Escopo `gmail.send` em `ESCOPOS`. Conector antigo sem esse escopo: tela mostra "reconectar para enviar e-mails" e a Tool `gmail_send` não é registrada para ele.
- Tabela `email_drafts` (migração `0014`).
- Tool `gmail_send(para, assunto, corpo, thread_id?)`: cria Rascunho, evento `email_draft_created`, devolve id e aviso. Nasce desligada por Conversa.
- `POST /api/conectores/google/drafts/{id}/enviar` e `/descartar`, só o dono. Enviar monta MIME (RFC 2822, base64url) com `In-Reply-To`/`References` quando há `thread_id`, chama `users/me/messages/send`, grava `message_id`, evento `email_sent`. Erro do Gmail devolve texto legível e mantém o Rascunho pendente.
- Front: o chat renderiza o Rascunho (para, assunto, corpo) com botões "Enviar" e "Descartar"; depois do clique mostra o estado. Texto no chat nunca envia.
- `gmail_read` passa a devolver `thread_id` e `message_id` para o modelo conseguir responder na thread.

**HITL (Toneli):** no GCP, adicionar o escopo `.../auth/gmail.send` ao consent screen. Reconectar a conta em `/conectores`. Validar: "responde o último e-mail do X dizendo que confirmo a reunião" → rascunho na tela → Enviar → e-mail na caixa de saída, na mesma thread.

**Aceite:**
- [x] Teste: turno com `gmail_send` ligada cria Rascunho `pendente` e não chama a API de envio (mock sem hit em `messages/send`).
- [x] Teste: `POST .../enviar` pelo dono chama `messages/send` com `threadId` e header `In-Reply-To` quando há original; por outro usuário devolve 404.
- [x] Teste: mensagem "pode enviar" no chat não muda o estado do Rascunho.
- [x] Eventos `email_draft_created` e `email_sent` na auditoria.
- [x] Screenshot dark do Rascunho com botões: `25-rascunho-email.png`.

## Answer
AFK feito. Migração 0014 (`email_drafts` e `tools.padrao_ligada`), escopo `gmail.send`, Tool `gmail_send` que só cria Rascunho, `GET/enviar/descartar` em `/api/connectors/google/drafts/{id}` (só o dono, trava de linha contra clique duplo), `gmail_read` devolve `message_id` e `thread_id`. Front: cartão do Rascunho na mensagem com Enviar/Descartar e estado lido do servidor; `/conectores` avisa "Reconecte para enviar e-mails".
Ressalvas: caminho `/api/connectors` em vez de `/api/conectores`; Rascunho liga-se ao `tool_call_id`, não à Mensagem (ver DECISOES-AUTONOMAS 25). Testado só com Gmail mockado; HITL do escopo no GCP no MANHA.
Screens: `25-rascunho-email.png`, `25-rascunho-descartado.png`, `25-conectores-reconectar.png`.
