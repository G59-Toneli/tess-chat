# Lacunas conhecidas

Onde o código diverge do que os ADRs prometem, ou onde um agente deixou aresta. Ticket 19 lê isto para o README e o guia de entrevista. Cada item diz se já tem ticket.

## Crédito (ADR 0004)
- **Reserva estimada localmente**, ~3 caracteres por token (INFERIDO), em vez de `count_tokens`. O spike provou que `UsageLimits(count_tokens_before_request=True)` funciona. Trade-off: uma chamada `countTokens` extra por request. Decidir: emendar o ADR ou abrir ticket para trocar. **Sem ticket.**
- **Duas chamadas simultâneas** do mesmo usuário podem passar juntas do cap. Corrige com lock por usuário ou `SELECT ... FOR UPDATE` na reserva. **Sem ticket.**
- ~~Turno cortado pelo teto de tool calls não é cobrado~~ (06b). **Resolvido no ticket 30:** o Ledger recebe o uso real dos requests do turno cortado.
- **Anexo em base64 volta ao modelo em todo turno** e infla a reserva. **Ticket 09b.**

## Compactação (ADR 0006)
- Marcador "histórico compactado aqui" no turno ao vivo só aparece após recarregar.
- Caminho de resumo de um resumo existe no código, sem teste nem verificação manual.
- Em turno com tool, o input conta todos os requests somados; o gatilho pode disparar antes do esperado.
- Teste usa subclasse que mexe em atributo privado do Pydantic AI; pode quebrar em upgrade.

## Tools (ADR 0009)
- Timeout de tool MCP (15 s) corta o turno pelo mesmo caminho do servidor caído, mas sem teste automatizado (ticket 30).
- Com `web_search` desligada, o Gemini ainda pode chamar `web_fetch` numa URL do histórico. Comportamento correto pelo registro, mas pode surpreender.
- Toggle global aceita qualquer usuário logado. **Ticket 14** restringe a superuser.
- Duração da tool só aparece durante o stream, não no histórico.

## Resiliência (ADR 0012)
- Com o 3.8 fora, cada request tenta 3 vezes antes do fallback: turno com tool fica lento.
- Sem `OPENAI_API_KEY`, a cadeia tem só os dois Gemini.
- Preço do gemini-3.7-flash igual ao 3.8 (INFERIDO).
- Front não sinaliza retry: acontece antes do stream abrir.

## Auth e demo
- `JWT_SECRET` e `DEMO_PASSWORD` com default de dev. **Ticket 16** define no VPS.
- Senha demo fixa no front; precisa bater com `DEMO_PASSWORD`.

## Front
- Sem teste unitário no front; verificação é por fluxo no browser e screenshot.
- Bundle de 1,6 MB (streamdown). Code-split só se incomodar.
- `attachments.message_id` nulo e nome do PDF some ao recarregar. **Ticket 09b.**
