# 86 — MCP: validar o IP na hora da conexão (DNS rebinding)

**Type:** bug de segurança (api/)
**Status:** ready-for-agent
**Blocked by:** —
**Refs:** `app/mcp.py:70` (comentário "rebinding não coberto"), `validar_url` (`app/mcp.py:73`), `app/rede.py` (`ip_interno`), `docs/ESTUDO-JEV-MCP.md` seção 4. Achado na sessão de estudo de 29/09.

**Problema:** a URL do Servidor MCP só é validada contra SSRF no cadastro (`app/mcp.py:208`). A sonda (`alcancavel`) e o toolset do turno (`toolset`) resolvem o DNS de novo e conectam sem validar. Um usuário cadastra um domínio com IP público e depois troca o DNS para `10.0.0.5`: o próximo turno manda `initialize` para a rede interna do VPS.

## Escopo
1. Um transporte `httpx` (ou hook de conexão) que, a cada conexão nova, resolve o host, recusa IP interno com a mesma regra de `ip_interno` e conecta **no IP resolvido**, mantendo SNI e `Host` do nome original. Sem janela entre validar e usar.
2. Usar esse transporte no `MCPToolset` da sonda, do turno e do cadastro. Em `ENV=dev`, os hosts de `HOSTS_DEMO` continuam liberados.
3. Recusa no turno vira servidor fora do turno com `mcp_server_unreachable` (mensagem legível), como uma sonda que falha.
4. Conferir se o mesmo buraco existe em `web_fetch` e na Tool por API (`api_tools.py:263`); se existir e o mesmo transporte servir, aplicar; senão, registrar em DECISOES-AUTONOMAS.

## Aceite
- pytest: resolver falso que devolve IP público no cadastro e `10.0.0.5` no turno → servidor sai do turno, nenhum request sai para o IP interno, evento gravado.
- pytest: fluxo normal com o `mcp-demo` continua verde.
- Atualizar o comentário de `app/mcp.py:70`, a linha da tabela em `docs/ESTUDO-JEV-MCP.md` seção 4 e `docs/LACUNAS.md`.
- Chamadas reais: 0.
