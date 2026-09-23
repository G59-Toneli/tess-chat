# ADR 0013 — Envio de e-mail pelo Conector Google, só com confirmação do Usuário

**Status:** aceito, 2026-09-23. Revisa o ADR 0010 (conector somente leitura).

## Contexto
O ADR 0010 fixou o Conector Google como somente leitura. Pedido do Toneli em 23/09: o assistente também responde e-mails. É a primeira Tool do app com efeito fora do app: um e-mail enviado não volta. O modelo erra destinatário, tom e conteúdo; o Roteador (ADR 0005) e o prompt não são trilho suficiente para ação irreversível.

## Decisão
1. **Escopo** `gmail.send` somado aos escopos de leitura. Quem já conectou precisa reconectar; a tela de Conectores avisa.
2. **Duas fases, uma Tool.** A Tool `gmail_send` nunca envia direto. Ela grava um **Rascunho** (`email_drafts`: usuário, conversa, mensagem, para, assunto, corpo, `thread_id` opcional, estado `pendente|enviado|descartado`) e devolve ao modelo o id e o texto "rascunho criado, aguardando confirmação". O modelo mostra o rascunho ao Usuário.
3. **Confirmação é clique, não texto.** O front renderiza o Rascunho com botões "Enviar" e "Descartar". Só `POST /api/connectors/google/drafts/{id}/enviar`, autenticado pelo dono, chama a API do Gmail. Texto "pode enviar" digitado no chat não envia nada: o modelo não tem Tool de envio final.
4. **Resposta na thread.** Se o Usuário pediu para responder um e-mail lido por `gmail_read`, o Rascunho leva `thread_id`, `In-Reply-To` e `References` do original.
5. **Auditoria** (ADR 0007): `email_draft_created`, `email_sent` (com `message_id` do Gmail) e `email_draft_discarded`.
6. **Toggle.** `gmail_send` é uma Tool como as outras e nasce ligada por Conversa. Primeira versão nascia desligada; o Toneli emendou em 23/09 (migração 0015): a trava contra envio indevido é o clique em Enviar, não o toggle, então desligar por padrão só atrapalhava a demo.

### Alternativas descartadas
- **Enviar direto pela Tool.** Mais simples, mas o app passaria a executar ação irreversível por decisão do modelo. Recusado.
- **Confirmação por texto no chat** ("sim, envia"). O modelo decide se o texto é confirmação; erro de interpretação envia e-mail. Recusado.
- **Servidor MCP do Google.** Mesmo motivo do ADR 0010: preview fechado.

## Consequências
- Padrão para qualquer Tool futura com escrita externa: rascunho + confirmação por endpoint próprio.
- Migração nova (`email_drafts`). Escopo `gmail.send` no consent screen do GCP (HITL do Toneli).
- Custo: um turno a mais por e-mail (rascunho, depois clique). Aceitável.
