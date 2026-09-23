# Mapa — Desafio Tess AI (tess-chat)

## Destination

App de chat deployado em link público, com os 10 requisitos obrigatórios funcionando e auditáveis, mais MCP e conector Google. Toneli sabe defender cada decisão na entrevista. Vídeo curto gravado.

**Marco:** Camada 1 (obrigatórios) deployada e compartilhável até **sexta 26/09**. Camadas 2 e 3 depois.
**Prazo:** 29/09 12h (confirmar terça vs quarta com o CPO).

## Notes

- Glossário: `CONTEXT.md`. Decisões: `docs/adr/`. Pesquisa: `research/`.
- Toneli precisa entender cada decisão. Agente autônomo não decide arquitetura: encontrou decisão nova, grava `BLOCKED` no ledger e para.
- Subagentes sempre em Opus 5.5.
- Skills por ticket: `mattpocock-skills:tdd` na implementação. `typesafe:typesafe-ai` no ticket 11. `mattpocock-skills:wizard` nas tarefas HITL de infra.
- Três funções são **HITL** (Toneli escreve): débito de crédito (08), gate de confiança do Roteador (11), gatilho de compactação (12). O agente deixa `TODO(human)` e para.
- Execução autônoma: loop externo de `claude -p --model opus`, um ticket por invocação, testes como gate fora do Claude, commit por ticket. Rate limit do plano Max = esperar e repetir, não falhar. Ver `docs/WORKFLOW.md`.

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
- [ADR 0011](../../docs/adr/0011-deploy-compose-caddy-duckdns-oci.md) — compose + Caddy + DuckDNS no OCI.
- Grilling 2026-09-23 — auth FastAPI-Users; "adicionar tools" = nativas com toggle + servidores MCP do usuário; repo `tess-chat` privado; UI em pt-BR; arquivos no disco do VPS com metadados no Postgres.

## Not yet specified

- Formato exato do prompt de Resumo e valor de N turnos literais. Decide após o spike medir tokens reais.
- Layout do painel de créditos e auditoria. Decide quando o front base existir (07).
- Se o Roteador Jev também escolhe entre tools MCP ou só nativas. Decide após smoke test (11).
- Conteúdo do vídeo e ordem dos fluxos na demo (19).

## Out of scope

- Login Google como auth do app. Só se sobrar tempo após Camada 3.
- Servidor MCP próprio expondo as tools do Google. Opcional pós-Camada 3.
- RAG sobre PDFs. PDF vai nativo ao Gemini; sem embeddings.
- Tracing externo (Langfuse, Logfire). Auditoria é no app.
- Envio de e-mail ou escrita no Drive. Conector é somente leitura.
