# 09b — Anexo por referência, não por base64 na Mensagem

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 09
**Refs:** ADR 0004, 0006. Ressalvas do ticket 09.

**Problema:** o 09 grava o base64 do Anexo em `messages.parts`. Ele volta ao modelo e à estimativa de reserva em todo turno seguinte. Um PDF de 20 MB estoura o cap e o contexto. `attachments.message_id` fica nulo e o nome do PDF some ao recarregar.

**What to build:** `messages.parts` guarda só `{type: "attachment", attachment_id, nome, mime}`. Ao montar o histórico para o modelo (`_persistir` e o carregamento em `chat.py`/`anexos.py`), rehidratar do disco em `BinaryContent` **só para a mensagem do turno atual**; para turnos anteriores, substituir por texto curto `[anexo: nome.pdf, 3 páginas]` (o modelo já respondeu sobre ele e a resposta está no histórico). Configuração futura pode permitir reenviar. Preencher `attachments.message_id` ao persistir. Front mostra o chip com o nome ao recarregar. Sem migração, salvo se precisar de coluna (então 0011).

**Aceite:**
- [x] Teste: turno 2 depois de um anexo de 1 MB tem estimativa de reserva e `prompt_tokens` sem o peso do anexo.
- [x] Teste: `attachments.message_id` preenchido; recarregar a conversa mostra o nome do arquivo.
- [x] Teste do 09 continua verde: no turno do anexo, o modelo recebe o `BinaryContent`.

## Answer
`messages.parts` guarda o `FileUIPart` do front com url `/api/attachments/{id}`; o data URI só existe na cópia que vai ao run. `_historico` troca todo arquivo de turno anterior por `[anexo: nome]`, inclusive na Compactação e em linhas antigas do 09. `_persistir` preenche `attachments.message_id` e põe `attachment_ids` no `message_sent`. Front sem mudança: o chip já lia `filename`.
Ressalvas: sem contagem de páginas no texto; tipo `file` do AI SDK em vez de `attachment` (DECISOES-AUTONOMAS). O "prompt_tokens" do aceite é medido pelo corpo HTTP que sai para o Gemini (GoogleModel + MockTransport): o stream do FunctionModel fixa input em 50. A reserva é checada espiando o valor passado a `reservar`.
