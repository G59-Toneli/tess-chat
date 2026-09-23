# 57 — OAuth abandonado não deixa Servidor MCP pendente

**Type:** task (api/ + web/)
**Status:** ready-for-agent
**Blocked by:** 52, 56 (resolved)
**Refs:** ADR 0022, ticket 52, ticket 56. Achado do E2E de 23/09, pedido do Toneli.

**Problema:** `POST /api/mcp-servers/oauth/iniciar` grava a linha em `mcp_servers` com `estado=aguardando_oauth` antes do consentimento (`api/app/mcp_oauth.py:243`). Se o usuário fecha a tela do provedor sem autorizar, sobra um card "aguardando autorização" em "Meus servidores". No E2E isso aconteceu com o Linear. Com `sid`, a tentativa de reconectar já desliga o servidor existente antes de o usuário autorizar.

**Decisão (orquestrador, 23/09):** o estado pendente sai do banco e vai para o cookie que já leva o `code_verifier`.
- O `iniciar` não grava nada no banco. Ele monta o pendente: `code_verifier`, `nome`, `url`, `sid?` e o dict `oauth` do DCR (client_id, client_secret?, token_endpoint, resource, scope). O pendente vai cifrado com `_fernet()` num cookie httpOnly, com `path` no callback, validade igual à do state, `samesite=lax` e `secure` em prod.
- O state JWT continua levando só `sub`, mais um `nonce` que também fica no cookie. O callback confere que os dois batem, e isso amarra o cookie ao state.
- O callback decifra o cookie. Cookie ausente ou inválido volta com `erro=pkce_ausente`. Só depois da troca do code dar certo, o callback cria a linha (sem `sid`) ou atualiza a linha do usuário (com `sid`) e lista as tools, como hoje.
- Reconectar abandonado deixa o servidor exatamente como estava.
- Alternativa descartada: manter a linha e esconder/purgar as pendentes num job. Continua gravando lixo e exige filtro em toda leitura.
- Fora do escopo: o app registrado no provedor a cada clique (DCR sem reaproveitamento). Fica registrado como lacuna.

**Limpeza:** migração `0022_mcp_sem_pendentes.py` apaga as linhas `estado='aguardando_oauth'` sem tools no registro. O downgrade é no-op. Se o front perder o uso do estado `aguardando_oauth`, remova o badge e o texto; o valor pode ficar no enum do banco.

**Docs:**
- Atualize o ADR 0022 com uma nota "Atualizado no ticket 57": onde vive o estado pendente e por quê.
- Adicione uma linha em `docs/LACUNAS.md` sobre o DCR a cada clique.
- `REVISAR(human)` no cookie do pendente.

## Aceite
- `iniciar` sem `sid` não cria linha: a contagem em `mcp_servers` fica igual e a lista `GET /api/mcp-servers` não muda.
- Callback com cookie válido cria o servidor `ok`, `ativo`, com as tools do mcp-demo.
- Reconectar com `sid` e abandonar: o servidor continua com o mesmo `estado`, `ativo` e `headers`.
- Callback com cookie de outro fluxo (nonce diferente do state) volta com erro e não cria nada.
- Callback sem cookie volta com `erro=pkce_ausente`.
- A migração 0022 apaga uma linha pendente sem tools e mantém uma `ok`.
- Os testes existentes de `test_mcp_oauth` e `test_mcp` continuam passando.
- `npm run build` limpo.
