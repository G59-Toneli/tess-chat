# ADR 0020 — Continuar conversa compartilhada por fork

**Status:** aceito, 2026-09-23. Complementa o ADR 0008.

## Contexto
O link público (ADR 0008) é só leitura. Decisão do Toneli em 23/09: quem abre o link pode continuar a conversa.

## Decisão
1. **Fork.** `POST /api/s/{share_id}/fork`, autenticado, cria uma Conversa nova do Usuário logado, título `<título> (cópia)`, com cópia das Mensagens até o corte do link. A Conversa do dono não muda. Mesmo comportamento de ChatGPT e Claude.
2. **Nada acionável da conta do dono.** Anexo vira texto `[anexo: nome]`, sem bytes (o arquivo é do dono, ADR 0016 só reenvia anexo próprio). Rascunho leva o estado real do momento e `copia: true`: o card fica só leitura, e o endpoint de envio já responde 404 para quem não é dono (ADR 0013). Resultado de tool fica como histórico. Colunas de uso (tokens, modelo) não são copiadas: descrevem os turnos do dono.
3. **Mesmas regras do link.** Revogado e inexistente: 404 igual (ADR 0008). Sem login: 401. O dono pode fazer fork do próprio link.
4. **Crédito.** O fork não chama modelo e não cobra. Os turnos seguintes cobram do Usuário da cópia como qualquer turno.
5. **Auditoria.** `share_forked` com `share_id`, `conversa_origem`, `conversa_nova`.
6. **Sem migração.** A origem da cópia fica no Evento de auditoria. Coluna `forked_from_share_id` só se uma tela precisar dela.

### Alternativas descartadas
- **Escrever na Conversa do dono.** Terceiros gastariam Crédito, Conectores e Tools do dono, e os turnos cairiam na auditoria dele. Quebra a privacidade de quem compartilhou.
- **Copiar os bytes dos anexos.** Duplica arquivo do dono na conta de outro sem ação do dono.

## Consequências
- A cópia não herda Resumo da Compactação do dono. Histórico longo compacta de novo na conta do visitante, que paga.
- Deslogado: o botão leva ao login, que volta ao link (`/login?proximo=`). O fork exige um segundo clique.
