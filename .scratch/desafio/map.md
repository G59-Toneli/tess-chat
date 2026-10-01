# Mapa — Desafio Tess AI (tess-chat)

## Destination

App de chat deployado em link público, com os 10 requisitos obrigatórios funcionando e auditáveis, mais MCP e conector Google. Cada decisão tem o porquê registrado. Vídeo curto gravado.

**Marco:** Camada 1 (obrigatórios) deployada e compartilhável até **sexta 26/09**. Camadas 2 e 3 depois.
**Prazo:** terça 29/09, 12h. Confirmado com a empresa.

## Notes

- Glossário: `CONTEXT.md`. Decisões: `docs/adr/`. Pesquisa: `research/`.
- Toneli precisa entender cada decisão. Decisão não coberta por ADR: o agente escolhe a opção mais simples que atende o aceite, registra em `docs/DECISOES-AUTONOMAS.md` e segue.
- Subagentes sempre em Opus 5.5.
- Skills por ticket: `mattpocock-skills:tdd` na implementação. `typesafe:typesafe-ai` no ticket 11. `mattpocock-skills:wizard` nas tarefas HITL de infra.
- Execução: sessão orquestradora do Claude Code dispara um agente executor por ticket (tool `Agent`), commit `feat(NN)` por ticket com `git commit --only`, orquestrador confere e dá push. Suíte completa em lote no fim do bloco. Ver `docs/WORKFLOW.md`.

## Estado dos tickets

Fonte: status em `issues/` e `LEDGER.md`. Atualizado em 23/09 ~04:00.

- **Resolvidos:** 01, 03, 04, 05, 06, 06b, 07, 07a, 07b, 07c, 08, 09, 09b, 10, 11, 12, 13, 14, 15, 17, 18 (AFK), 19 (AFK), 20, 21, 22, 23, 24.
- **Bloqueados em Toneli:** 02 e 16. Precisam das chaves SSH do VPS e do registro A `chat.toneli.dev.br` (ver `MANHA.md`). Parte HITL do 18 (conectar conta Google) e do 19 (gravar vídeo) também no `MANHA.md`.
- **Suíte final do bloco (23/09):** 141 testes verdes, build e tsc limpos.

## Decisions so far

- [ADR 0001](../../docs/adr/0001-backend-python-pydantic-ai.md) — FastAPI + Pydantic AI, generateContent.
- [ADR 0002](../../docs/adr/0002-front-vite-servido-pelo-fastapi.md) — Vite + shadcn + AI Elements servido pelo FastAPI, um container.
- [ADR 0003](../../docs/adr/0003-modelo-gemini-flash-pago.md) — gemini-3.8-flash pago; flash-lite para resumo.
- [ADR 0004](../../docs/adr/0004-credito-em-micro-dolar-do-uso-real.md) — crédito em micro-USD do uso real, ledger append-only, reserva/acerto, cap duplo.
- [ADR 0005](../../docs/adr/0005-jev-como-roteador-pre-chamada.md) — Jev como Roteador pré-chamada com gate.
- [ADR 0006](../../docs/adr/0006-compactacao-por-resumo-com-limiar-configuravel.md) — compactação por resumo, limiar em Configuração.
- [ADR 0007](../../docs/adr/0007-auditoria-append-only.md) — audit_events append-only com REVOKE, tela no app.
- [ADR 0008](../../docs/adr/0008-compartilhamento-por-corte.md) — share por corte, 404 uniforme, noindex.
- [ADR 0009](../../docs/adr/0009-registro-unico-de-tools-e-mcp-client.md) — registro único de tools; busca/fetch próprios; MCP só Streamable HTTP.
- [ADR 0010](../../docs/adr/0010-conector-google-oauth-direto.md) — conector Google por OAuth direto, 3 tools read-only.
- [ADR 0011](../../docs/adr/0011-deploy-compose-caddy-duckdns-oci.md) — compose + Caddy + chat.toneli.dev.br no OCI.
- [ADR 0012](../../docs/adr/0012-resiliencia-retry-e-fallback-de-modelo.md) — retry com backoff, FallbackModel Gemini→Gemini→OpenAI, observabilidade do turno em audit_events.
- [Spike 01](../../spike/RESULTADO.md) — 9/9 hipóteses passaram; usage cumulativo por chunk, thinking separado, MCPToolset dual-era OK, Jev 9/9 em pt-BR.
- Grilling 2026-09-23 — auth FastAPI-Users; "adicionar tools" = nativas com toggle + servidores MCP do usuário; repo `tess-chat` privado; UI em pt-BR; arquivos no disco do VPS com metadados no Postgres.

## Not yet specified

- Formato exato do prompt de Resumo e valor de N turnos literais. Decide após o spike medir tokens reais.
- Layout do painel de créditos e auditoria. Decide quando o front base existir (07).
- Se o Roteador Jev também escolhe entre tools MCP ou só nativas. Decide após smoke test (11).
- Conteúdo do vídeo e ordem dos fluxos na demo (19). Resolvido: roteiro no README.

## Out of scope

- Login Google como auth do app. Só se sobrar tempo após Camada 3.
- Servidor MCP próprio expondo as tools do Google. Opcional pós-Camada 3.
- RAG sobre PDFs. PDF vai nativo ao Gemini; sem embeddings.
- Tracing externo (Langfuse, Logfire). Auditoria é no app.
- Envio de e-mail ou escrita no Drive. Conector é somente leitura.
