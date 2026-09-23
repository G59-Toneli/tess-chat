# 23 — MCP: servidor caído não derruba o turno; bloquear URL interna

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 21
**Refs:** ADR 0009, ressalvas do ticket 17 em `docs/DECISOES-AUTONOMAS.md`, `api/app/resiliencia.py` (06b).

**Problema:** (1) servidor MCP que cai depois do cadastro derruba o turno inteiro nas conversas do dono; hoje o contorno é desligar o servidor em `/mcp`. (2) A URL do servidor é livre: risco de SSRF para endereço interno (127.0.0.1, 10.x, 169.254.x, metadata da nuvem).

**What to build:** (1) ao montar os toolsets do turno, testar o servidor com timeout curto; se falhar, seguir sem as tools dele, emitir evento `mcp_server_unreachable` e avisar no chat com texto curto. (2) Validar URL no cadastro: só `https://` (exceto `http://` para host `mcp-demo`/`127.0.0.1` quando `ENV=dev`), rejeitar IP privado e link-local após resolver o DNS. Registrar decisão.

**Aceite:**
- [x] Teste: servidor demo derrubado no meio, turno seguinte responde e o evento aparece.
- [x] Teste: cadastro com `http://169.254.169.254/` e `http://10.0.0.1/` devolve 422 legível.

## Answer
Sonda de 3 s por Servidor MCP ao montar o toolset do turno (`mcp.alcancavel`, em paralelo); caído sai do turno, grava `mcp_server_unreachable` e o stream ganha um aviso curto. Cadastro valida a URL (`mcp.validar_url`): só https, todo IP resolvido precisa ser público, 422 com texto; em `ENV=dev` o demo (`mcp-demo`, `127.0.0.1`) passa em http.
Teste de queda usa o server.py do demo em subprocesso derrubado no meio (mesmo código do container), não `docker compose stop`.
Ressalvas: produção precisa `ENV=prod` (default é `dev`); DNS rebinding não coberto (checagem só no cadastro); servidor que cai entre a sonda e o run ainda derruba o turno.
REVISAR(human): `validar_url` em `api/app/mcp.py`.
