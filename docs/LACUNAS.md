# Lacunas conhecidas

Onde o código diverge do que os ADRs prometem, ou onde um agente deixou aresta. Ticket 19 lê isto para o README e o guia de entrevista. Cada item diz se já tem ticket.

## Crédito (ADR 0004)
- ~~Reserva estimada localmente em vez de `count_tokens`~~. **Decidido pelo Toneli em 23/09 ([ADR 0019](adr/0019-reserva-por-estimativa-local.md)):** fica a estimativa local, ~3 caracteres por token (INFERIDO). A reserva só segura crédito; o acerto usa o uso real.
- **Duas chamadas simultâneas** do mesmo usuário podem passar juntas do cap. Corrige com lock por usuário ou `SELECT ... FOR UPDATE` na reserva. **Sem ticket.**
- ~~Turno cortado pelo teto de tool calls não é cobrado~~ (06b). **Resolvido no ticket 30:** o Ledger recebe o uso real dos requests do turno cortado. Toneli confirmou manter a cobrança em 23/09.
- ~~Anexo em base64 volta ao modelo em todo turno e infla a reserva~~. **Intencional ([ADR 0016](adr/0016-imagem-do-historico-volta-com-bytes.md)):** sem os bytes o modelo inventava o conteúdo. O prefixo igual entre turnos deixa o cache implícito do Gemini cobrir.

## Compactação (ADR 0006)
- ~~Marcador "histórico compactado aqui" no turno ao vivo só aparece após recarregar~~. **Resolvido nos tickets 49 e 51:** o separador "Histórico anterior resumido" aparece antes da pergunta do turno que compactou, sem recarregar.
- Caminho de resumo de um resumo existe no código, sem teste nem verificação manual.
- Em turno com tool, o input conta todos os requests somados; o gatilho pode disparar antes do esperado.
- Teste usa subclasse que mexe em atributo privado do Pydantic AI; pode quebrar em upgrade.

## Tools (ADR 0009)
- Timeout de tool MCP (15 s) corta o turno pelo mesmo caminho do servidor caído, mas sem teste automatizado (ticket 30).
- Com `web_search` desligada, o Gemini ainda pode chamar `web_fetch` numa URL do histórico. Comportamento correto pelo registro, mas pode surpreender.
- ~~Toggle global aceita qualquer usuário logado~~. **Resolvido:** `PUT /api/tools/{nome}` exige superuser (`Admin`, `api/app/tools.py`).
- Duração da tool só aparece durante o stream, não no histórico.

## Resiliência (ADR 0012)
- Com o 3.8 fora, cada request tenta 3 vezes antes do fallback: turno com tool fica lento.
- ~~Sem `OPENAI_API_KEY`, a cadeia tem só os dois Gemini.~~ **Decidido pelo Toneli em 23/09 ([ADR 0018](adr/0018-fallback-so-entre-geminis.md)):** sem fallback OpenAI. Queda do Google inteiro derruba o chat.
- Preço do gemini-3.7-flash igual ao 3.8 (INFERIDO).
- Front não sinaliza retry: acontece antes do stream abrir.

## Deploy (ADR 0014)
- **Teste de reboot do VPS adiado** pelo Toneli em 23/09. O VPS é produção do trabalho. Testado só `down` + `up` sem `-v` (ticket 16).

## Auth e demo
- ~~`JWT_SECRET` com default de dev~~. **Resolvido:** em produção está definido, com 64 caracteres, e não é o default (verificado em 2026-09-23). Com `ENV=prod`, o boot recusa segredo default ou curto. `DEMO_PASSWORD` com default de dev: não verificado.
- Senha demo fixa no front; precisa bater com `DEMO_PASSWORD`.

## Front
- Sem teste unitário no front; verificação é por fluxo no browser e screenshot.
- Bundle de 1,6 MB (streamdown). Code-split só se incomodar.
- ~~`attachments.message_id` nulo~~. **Resolvido no ticket 09b:** `ligar_a_mensagem` (`api/app/anexos.py`) liga o anexo à Mensagem no fim do turno. Nome do PDF ao recarregar: não verificado.
