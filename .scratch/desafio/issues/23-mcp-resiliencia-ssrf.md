# 23 — MCP: servidor caído não derruba o turno; bloquear URL interna

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 21
**Refs:** ADR 0009, ressalvas do ticket 17 em `docs/DECISOES-AUTONOMAS.md`, `api/app/resiliencia.py` (06b).

**Problema:** (1) servidor MCP que cai depois do cadastro derruba o turno inteiro nas conversas do dono; hoje o contorno é desligar o servidor em `/mcp`. (2) A URL do servidor é livre: risco de SSRF para endereço interno (127.0.0.1, 10.x, 169.254.x, metadata da nuvem).

**What to build:** (1) ao montar os toolsets do turno, testar o servidor com timeout curto; se falhar, seguir sem as tools dele, emitir evento `mcp_server_unreachable` e avisar no chat com texto curto. (2) Validar URL no cadastro: só `https://` (exceto `http://` para host `mcp-demo`/`127.0.0.1` quando `ENV=dev`), rejeitar IP privado e link-local após resolver o DNS. Registrar decisão.

**Aceite:**
- [ ] Teste: servidor demo derrubado no meio, turno seguinte responde e o evento aparece.
- [ ] Teste: cadastro com `http://169.254.169.254/` e `http://10.0.0.1/` devolve 422 legível.
