# 59 — Tool por API (back): cadastro low-code de tool HTTP

**Type:** task (api/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ADR 0009 (registro único de tools), ticket 17 e 23 (SSRF), `api/app/tools.py`. Pedido do Toneli em 23/09. Requisito do desafio: "Possibilidade de adicionar e utilizar tools, incluindo acesso à internet e web scraping."

**Problema:** hoje uma tool nova só entra por Servidor MCP. Queremos que um usuário não técnico cadastre uma tool a partir de uma API HTTP qualquer, sem código. A Tess lista "Custom API" como *Coming soon* (docs.tess.im/en/connectors.md).

**Decisão (Toneli, 23/09):** Tool por API, definida pelos campos abaixo.
- `nome`: slug `[a-z][a-z0-9_]*`, com até 40 chars.
- `descricao`: o que a tool faz, para o modelo.
- `metodo`: `GET` | `POST`.
- `url`: com placeholders `{param}` no path ou na query.
- `parametros`: lista de `{nome, tipo: string|number|integer|boolean, descricao, obrigatorio}`.
- `corpo`: só no POST. É um template JSON com placeholders `"{param}"`, que viram o valor tipado.
- `auth`: `nenhuma` | `header` (nome + valor) | `bearer` (token).

Regras dos campos:
- Todo `{param}` da URL e do corpo precisa estar em `parametros`, e todo parâmetro obrigatório precisa aparecer em algum lugar. Um parâmetro não usado vira query string.
- O valor de `auth` vai cifrado com `_cifrar` (o mesmo Fernet do MCP) e nunca volta para o front.

**Invariante: testar antes de salvar.** `POST /api/api-tools` recebe a definição mais `exemplo: {param: valor}`. O back executa o request real com o exemplo e só grava se a resposta for 2xx. Falha vira 422 ou 502 com texto legível e com o status e o começo do corpo. Nada fica no banco. É o mesmo invariante do cadastro de MCP (`mcp.py:178`).
Também existe `POST /api/api-tools/testar`, que executa e devolve `{status, corpo_cortado, ms}` sem gravar. A tela usa esse endpoint no botão "Testar".

**Execução (também no turno):**
- `validar_url` (`mcp.py:71`) roda na URL final, depois de substituir os placeholders.
- Os valores são URL-encoded no path e na query. Redirect segue até 3 saltos, validando cada um, como o `web_fetch` (`tools.py:42`).
- Timeout de 15 s.
- A resposta JSON sai compacta. Texto sai cru. Os dois passam por `cortar(..., LIMITE_CHARS_MCP)` (`tools.py:142`).
- Status fora de 2xx vira texto para o modelo ("A API respondeu 404: ..."), não exceção.
- Nunca manda o valor de auth para log ou auditoria.

**Registro:**
- Nova tabela `api_tools`: id, user_id, nome, descricao, metodo, url, parametros JSONB, corpo JSONB nulo, auth cifrado, created_at, UNIQUE(user_id, nome).
- Cada linha gera uma `Tool` com `origem='api'` e nome `api_<4hex>_<nome>`, com limite de 64. O schema sai de `parametros` e passa por `schema_para_modelo` (`tools.py:217`).
- `estado_da_conversa` (`tools.py:159`) mostra a tool só para o dono, igual às tools de origem `mcp`.
- `toolset_da_conversa` (`tools.py:310`) inclui um toolset das tools de API ativas, dentro de `Auditada` e `ComTeto`.
- A migração é a `0023_api_tools.py`. O RLS segue o padrão da `0013_mcp_servers.py`.

**Endpoints:** `GET /api/api-tools` (lista do usuário, sem segredo), `POST` (cadastra), `POST /testar`, `DELETE /{id}`. Não tem edição: o usuário remove e cadastra de novo. Auditoria: `api_tool_added`, `api_tool_removed`.

**Modelos prontos:** `GET /api/api-tools/modelos` devolve 3 definições completas, com exemplo:
- ViaCEP: `https://viacep.com.br/ws/{cep}/json/`;
- Open-Meteo: `https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code`;
- BrasilAPI CNPJ: `https://brasilapi.com.br/api/cnpj/v1/{cnpj}`.

**Docs:**
- `docs/adr/0024-tool-por-api.md`, com os porquês: por que HTTP e não código do usuário; por que testar antes de salvar; por que sem edição.
- Um termo novo em `CONTEXT.md`.

## Aceite (testes com `httpx.MockTransport`, sem rede real)
- Cadastro com exemplo 2xx grava a linha e a `Tool` com o schema certo: tipos, obrigatórios e descrições.
- Exemplo 404 ou timeout: 422/502 e nada no banco.
- Placeholder sem parâmetro e parâmetro obrigatório não usado: 422.
- URL que resolve para IP interno (antes e depois de substituir) e redirect para IP interno: recusados.
- O valor com `/`, espaço e `?` é encodado no path, e não muda a rota.
- O corpo POST sai com os tipos certos (number continua number).
- `auth` header e bearer chegam no request. A listagem não devolve o segredo. A auditoria não contém o segredo.
- No turno (`FunctionModel` do Pydantic AI), o modelo chama a tool e recebe o JSON cortado. Uma resposta 500 vira texto, sem quebrar o turno.
- A tool de API de um usuário não aparece na conversa de outro.
- Os testes existentes de `test_tools` e `test_mcp` continuam passando.

## Answer
`api/app/api_tools.py` (tabela `api_tools`, migração 0023, endpoints `GET/POST /api/api-tools`, `POST /testar`, `GET /modelos`, `DELETE /{id}`) e registro com origem `api` em `tools.py` (coluna `api_tool_id`, dono em `estado_da_conversa`, toolset via `Tool.from_schema`, filtro do catálogo). 20 testes em `test_api_tools.py` com MockTransport; test_tools/mcp/mcp_oauth/conectores seguem verdes.
Ressalvas: exemplo fora de 2xx dá 502 (422 fica para regra e SSRF); placeholder no host é recusado; valores do formulário são coeridos pelo tipo. Decisões autônomas registradas no ADR 0024 (o DECISOES-AUTONOMAS estava em edição por outra sessão). DNS rebinding segue não coberto.
