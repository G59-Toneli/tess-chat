# 46 — "Continuar esta conversa" a partir do link (fork para a conta de quem está logado)

**Type:** task (AFK, api/ e web/)
**Status:** resolved
**Blocked by:** 45 (mesma página `Compartilhamento.tsx`)
**Refs:** ADR 0008, ADR 0013, ADR 0005/0006 se tratarem de crédito e auditoria. Decisão do Toneli em 23/09.

**Decisão (Toneli, 23/09):** fork. Quem está logado e abre `/s/<id>` pode clicar "Continuar esta conversa": o sistema cria uma Conversa nova do visitante com cópia das Mensagens até o corte do link. A conversa do dono não muda. Alternativa descartada: escrever na conversa do dono (crédito, conectores e auditoria do dono usados por terceiros; privacidade). Mesmo comportamento de ChatGPT e Claude. Escrever ADR novo (próximo número livre em `docs/adr/`, confira na hora: outra sessão cria ADRs) complementando o 0008.

**What to build:**
- `POST /api/s/{share_id}/fork` (autenticado): valida share ativo, cria Conversa do usuário logado com título "<título> (cópia)" e copia as Mensagens até `last_message_id`, preservando ordem e `parts`. Devolve o id da Conversa nova. Evento de auditoria `share_forked` (share_id, conversa de origem, conversa nova).
- Na cópia, nada que dependa da conta do dono continua acionável: card de rascunho de e-mail vira só leitura (o Rascunho do dono não é copiado nem enviável), bytes de anexo não são copiados (ficam como `[anexo: nome]`), resultado de tool fica como histórico.
- O dono pode fazer fork do próprio link (vira cópia normal).
- Página pública: botão "Continuar esta conversa". Logado: chama o fork e navega para a Conversa nova. Deslogado: vai para o login e volta ao link depois (ou faz o fork direto após login).
- Crédito: o fork não cobra; os turnos seguintes cobram do visitante como qualquer turno.
- Migração só se precisar (ex.: `forked_from_share_id`); próximo número livre em `api/migrations/versions`.

**Aceite:**
- [ ] Teste: fork cria Conversa do visitante com as Mensagens até o corte e não altera a do dono.
- [ ] Teste: share revogado ou inexistente devolve 404 no fork; sem login devolve 401.
- [ ] Teste: primeiro turno na cópia usa o histórico copiado (FunctionModel vê as mensagens anteriores) e cobra do visitante.
- [ ] Teste: rascunho copiado não é enviável pelo visitante.
- [ ] Screenshot dark do botão no link e da Conversa copiada aberta.
- [ ] ADR escrito. Sem chamada real a Gemini, Tavily ou Jev.

## Answer
`POST /api/s/{id}/fork` em `api/app/shares.py`: Conversa nova do logado, "<título> (cópia)", Mensagens até o corte, evento `share_forked`. Sem migração, sem cobrança (ADR 0020).
Anexo vira `[anexo: nome]`; Rascunho leva o estado real e `copia: true` (card só leitura; envio pelo visitante já é 404). Tokens e modelo do dono não são copiados.
Front: botão "Continuar esta conversa" no banner do link; deslogado vai a `/login?proximo=/s/<id>` e volta ao link (fork pede outro clique).
Ressalva: `[anexo: nome]` sem o aviso do ADR 0016; o modelo pode descrever a imagem que não vê. A cópia não herda o Resumo da Compactação.
Screenshots: `screens/46-link-continuar.png`, `screens/46-conversa-copiada.png`.
