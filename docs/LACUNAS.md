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
- Em turno com tool, o input conta todos os requests somados; o gatilho pode disparar antes do esperado. Ticket 58: o turno Notion (msg 222) somou 1.251.511 com ~17 requests de ~75k cada; o turno seguinte compacta com uma janela real bem abaixo de 100k. Opções: (a) gatilho lê o `input_tokens` do último `llm_request` do turno anterior (maior fidelidade à janela; muda o gatilho, precisa de ADR); (b) manter a soma e subir o limiar (simples, mas o limiar perde significado de janela). Recomendo (a).
- Teste usa subclasse que mexe em atributo privado do Pydantic AI; pode quebrar em upgrade.

## Tools (ADR 0009)
- Timeout de tool MCP (15 s) corta o turno pelo mesmo caminho do servidor caído, mas sem teste automatizado (ticket 30).
- Com `web_search` desligada, o Gemini ainda pode chamar `web_fetch` numa URL do histórico. Comportamento correto pelo registro, mas pode surpreender.
- ~~Toggle global aceita qualquer usuário logado~~. **Resolvido:** `PUT /api/tools/{nome}` exige superuser (`Admin`, `api/app/tools.py`).
- Duração da tool só aparece durante o stream, não no histórico.
- Servidor MCP por OAuth: cada clique em Conectar ou Reconectar faz um DCR novo, e o provedor acumula apps registrados, inclusive dos fluxos abandonados. Sem reaproveitar o `client_id` (ticket 57, ADR 0022).

## Resiliência (ADR 0012)
- Com o 3.8 fora, cada request tenta 3 vezes antes do fallback: turno com tool fica lento.
- ~~Sem `OPENAI_API_KEY`, a cadeia tem só os dois Gemini.~~ **Decidido pelo Toneli em 23/09 ([ADR 0018](adr/0018-fallback-so-entre-geminis.md)):** sem fallback OpenAI. Queda do Google inteiro derruba o chat.
- Preço do gemini-3.7-flash igual ao 3.8 (INFERIDO).
- Front não sinaliza retry: acontece antes do stream abrir.

## Deploy (ADR 0014)
- **Teste de reboot do VPS adiado** pelo Toneli em 23/09. O VPS é produção do trabalho. Testado só `down` + `up` sem `-v` (ticket 16).

## Auth e demo
- ~~`JWT_SECRET` com default de dev~~. **Resolvido:** em produção está definido, com 64 caracteres, e não é o default (verificado em 2026-09-23). Com `ENV=prod`, o boot recusa segredo default ou curto. `DEMO_PASSWORD` trocado por valor aleatório em produção em 2026-09-23.
- ~~Senha demo fixa no front~~. **Resolvido:** o front não carrega mais a senha.

## Front
- Sem teste unitário no front; verificação é por fluxo no browser e screenshot.
- Bundle de 1,6 MB (streamdown). Code-split só se incomodar.
- ~~`attachments.message_id` nulo~~. **Resolvido no ticket 09b:** `ligar_a_mensagem` (`api/app/anexos.py`) liga o anexo à Mensagem no fim do turno. Nome do PDF ao recarregar: não verificado.

## Segurança (revisão final, 23/09)
- Senha demo fixa no front: **resolvido** (rev-a1). O front não tem mais a senha, e a conta demo não é admin. Admin vem de `ADMIN_EMAIL`.
- Corrida no Cap: duas requisições paralelas do mesmo Usuário leem o saldo antes de a outra reservar. O gasto pode passar do Cap pelo custo de um turno.
- DNS rebinding: o MCP valida a URL só no cadastro, e o web_fetch valida antes do request. Nos dois, o httpx resolve o DNS de novo; um host que troca de IP entre as duas resoluções passa.
- Tavily (web_search) e Jev (Roteador) ficam fora do Ledger: o custo deles não entra no Crédito nem no Cap.
- Sem Content-Security-Policy. Risco de quebrar a SPA (Streamdown, Mermaid, estilos inline) perto do prazo. Os outros headers de segurança estão no nginx.

## Custo fixo por chamada (ticket 58)
- Cada request leva system prompt + todas as tool defs ativas. Medido local com o MCP falso de 12 tools (`tests/fixtures/mcp_grande.py`, 43k chars): 9.523 tokens de prefixo, 9.328 só nas tools. Em produção, com 61 a 64 tools, o ticket INFERE ~65k. Opções, todas mudam o conjunto de tools e não foram aplicadas: (a) mandar só as tools do servidor que o Roteador sugerir, mais as nativas; (b) tool de descoberta (`listar_tools_do_servidor`) com as defs carregadas sob demanda; (c) o Usuário desligar servidores na Conversa (já existe, é manual).
- Conjunto de tools muda entre turnos (rodapé 64 → 61). O contador do rodapé vem de `estado_da_conversa` (toggle da Conversa, `ativa_global`, `McpServer.ativo`, Conector Google), não da sonda. Qualquer mudança nesse conjunto troca o prefixo e zera o cache implícito. Causa exata não confirmada: consultar `tool_toggled`, `tool_toggled_global`, `mcp_server_toggled`, `mcp_server_unreachable`, `mcp_oauth_refresh_failed` entre as msgs 222 e 232.
- Cache implícito do Gemini é best-effort: mínimo 4.096 tokens no 3.x Flash, TTL não documentado ("requests com prefixo parecido em pouco tempo", ai.google.dev/gemini-api/docs/caching). Intervalo longo entre turnos zera o cache sem bug nenhum. Opção: cache explícito (`google_cached_content`) com system prompt + tools, por Usuário e conjunto de tools; o Pydantic AI tira `tools` e `system_instruction` do request quando ele está setado, então o cache precisa contê-los. Custo de armazenamento por hora e invalidação a cada mudança de tool.
- `tool_config` muda no 1º request quando o Roteador força uma Tool (ANY + `allowed_function_names`). Se isso entra na chave do cache implícito: INFERIDO, não documentado.
- `llm_request` só sai quando o turno grava (`_persistir`). Turno que termina em `llm_error` não emite por chamada.
