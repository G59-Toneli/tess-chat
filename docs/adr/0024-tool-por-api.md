# ADR 0024 — Tool por API: API HTTP vira Tool por formulário, testada antes de salvar

**Status:** aceito, 2026-09-23. Complementa o [ADR 0009](0009-registro-unico-de-tools-e-mcp-client.md). Ticket 59.

## Contexto
Até aqui uma Tool nova só entrava por Servidor MCP. Quem não tem servidor MCP e quer que o modelo consulte uma API pública (CEP, clima, CNPJ) precisava escrever código. O requisito do desafio pede "adicionar e utilizar tools, incluindo acesso à internet". A Tess lista "Custom API" como *Coming soon* (docs.tess.im/en/connectors.md). O Toneli pediu em 23/09 um cadastro low-code para usuário não técnico.

## Decisão
1. **Definição declarativa de um request HTTP.** `nome`, `descricao`, `metodo` (GET | POST), `url` com `{param}` no caminho ou na query, `parametros` (`nome`, `tipo` string | number | integer | boolean, `descricao`, `obrigatorio`), `corpo` (template JSON, só no POST) e `auth` (nenhuma | header | bearer). A linha mora em `api_tools` (migração 0023). O schema que o modelo recebe sai de `parametros`.
2. **Testar antes de salvar.** `POST /api/api-tools` recebe a definição e um `exemplo`, executa o request real e só grava com resposta 2xx. Regra violada ou URL recusada: 422. API fora de 2xx, timeout ou erro de rede: 502 com status e começo do corpo. Nada fica no banco. `POST /api/api-tools/testar` executa sem gravar.
3. **Sem edição.** `GET`, `POST`, `DELETE /{id}`. Para mudar, o Usuário remove e cadastra de novo.
4. **Registro único.** Cada linha gera uma Tool com `origem='api'`, nome `api_<4 hex do id>_<nome>` e FK `tools.api_tool_id` com cascade. Só o dono vê a Tool, na Conversa e no catálogo `GET /api/tools`. O turno monta a Tool com `Tool.from_schema` do Pydantic AI, dentro de `Auditada` e `ComTeto`.
5. **Execução.** Valores URL-encoded (`quote(safe="")`) no caminho e na query. `validar_url` roda na URL final e em cada redirect (até 3). Timeout de 15 s. JSON sai compacto, texto sai cru, os dois cortados em `LIMITE_CHARS_MCP`. Status fora de 2xx e falha de rede viram texto para o modelo. O valor de `auth` vai cifrado (Fernet, `CONNECTORS_KEY`) e não volta na listagem nem no Evento.

### Por quê
- **HTTP e não código do Usuário.** Código arbitrário exige sandbox (processo isolado, limite de CPU e memória, rede filtrada). É outra superfície de ataque inteira. Um request HTTP declarativo cobre o caso comum (API REST com parâmetros) e reaproveita a barreira de SSRF que já existe.
- **Testar antes de salvar.** O mesmo invariante do cadastro de MCP. Tool salva e quebrada só aparece no meio de um turno, e o modelo gasta crédito para descobrir. Testar no cadastro mostra o erro na hora, para quem pode corrigir.
- **Sem edição.** Editar exigiria testar de novo, trocar o schema de uma Tool que pode estar em Conversas abertas e decidir o que fazer com o segredo guardado (manter, trocar, apagar). Remover e cadastrar de novo cobre isso com o que já existe. O custo é redigitar o formulário, que os modelos prontos encurtam.

### Decisões autônomas (agente do ticket 59)
- **Exemplo fora de 2xx é 502, não 422.** O ticket aceita os dois. 422 fica para regra da definição e URL recusada (culpa do formulário); 502 para o que a API respondeu (mesma leitura do MCP).
- **Placeholder no host é recusado (422).** O ticket só prevê caminho e query. No host, o valor mudaria o destino depois da checagem de SSRF.
- **Coerção de tipo.** O formulário manda texto; o `Tool.from_schema` não valida argumento. `"3"` num `integer` vira `3`; valor que não converte vira 422 no cadastro e `ModelRetry` no turno.
- **`/testar` devolve o texto que o modelo receberia** (cortado em `LIMITE_CHARS_MCP`), não um trecho menor.
- **Texto do `validar_url`.** A função fala de "servidor MCP". O módulo troca por "API" na mensagem, sem mexer no `mcp.py`.

### Alternativas descartadas
- **Importar OpenAPI.** Cobre APIs grandes, mas usuário não técnico não tem o spec à mão e a maioria das APIs públicas simples não publica um.
- **Script do Usuário (Python ou JS) em sandbox.** Ver "HTTP e não código".
- **Seguir redirect pelo httpx (`follow_redirects=True`).** O salto não passaria por `validar_url`.

## Consequências
- DNS rebinding continua não coberto: o httpx resolve o DNS de novo depois da checagem (ressalva do ticket 23).
- Segredo colado na URL (ex.: `?key=...`) não é tratado como segredo: aparece na listagem e no Evento. O campo `auth` existe para isso.
- Header de auth por nome (tipo `header`) segue num redirect para outro host; o httpx só tira o `Authorization`.
- Em `ENV=dev`, o `validar_url` libera `127.0.0.1` e `mcp-demo` em http, também para Tool por API.
