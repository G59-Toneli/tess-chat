# 56 — Tela MCP: catálogo + URL única com detecção de auth

**Type:** task (web/ + api/app/mcp_oauth.py)
**Status:** ready-for-agent
**Blocked by:** 52 (resolved)
**Refs:** ticket 52, ADR 0022, `docs/UI-GUIA.md`. Pedido do Toneli em 23/09, depois de validar Notion e Stripe em produção.

**Problema:** a tela `/mcp` tem nome, URL, header e dois botões ("Conectar por OAuth" e "Conectar e listar tools"). O usuário não sabe se o servidor tem OAuth, então não sabe qual botão usar. O próprio Toneli não percebeu que o OAuth funciona para qualquer URL.

**Decisão (Toneli, 23/09):**
1. **Catálogo "Conectar em 1 clique"** no topo, só com Notion e Stripe. Um card para cada, com logo (SVG inline, sem dependência nova), uma linha do que faz ("páginas e bancos de dados" / "clientes, cobranças e links de pagamento") e um botão:
   - "Conectar", quando não tem servidor com essa URL;
   - "Conectado" com um check, quando o servidor está com estado `ok`;
   - "Reconectar", quando o estado é `expirado` ou `aguardando_oauth`.
2. **"Outro servidor"** tem só o campo URL e o botão "Conectar". O app decide o caminho, e o usuário não escolhe:
   - O servidor tem OAuth com DCR: redirect para o consentimento, igual ao 52.
   - O servidor não exige auth (o initialize sem token responde OK): cadastra direto, pelo caminho do POST atual sem header.
   - O servidor exige auth, mas não tem OAuth com DCR: o card expande um campo "Token de acesso" com texto explicando por quê ("Esse servidor não oferece login automático. Cole um token de acesso dele."). O envio usa o POST atual com `autorizacao`.
   - Erro real (URL inválida, SSRF, fora do ar): mensagem de erro, sem campo de token.
3. **Nome derivado do host** (ex.: `mcp.linear.app` vira "Linear"), editável num campo pequeno que só aparece depois da detecção. Nome duplicado ganha sufixo " 2".
4. **"Meus servidores"** continua com os cards de hoje (estado, Reconectar, Remover, toggle, Ver tools).

**Back:** `POST /api/mcp-servers/oauth/iniciar` passa a devolver um resultado discriminado, em vez do 422 genérico:
- `{modo: "oauth", id, url}` quando existe OAuth com DCR;
- `{modo: "sem_auth"}` quando o initialize sem token funcionou (o front então chama o POST atual sem header);
- `{modo: "token"}` quando veio 401/403 e falta metadata ou DCR.

SSRF e erro de rede continuam como 422/502 com mensagem. Não crie a linha `aguardando_oauth` nos modos `sem_auth` e `token`. Atualize os testes do 52 que esperavam 422 sem DCR.

## Aceite
- Teste de back para cada modo (`oauth`, `sem_auth` com o mcp-demo, `token`) e para o SSRF, que continua recusado.
- `npm run build` limpo.
- Screenshots no Brave (dark, 1440x900) em `.scratch/desafio/screens/56-*.png`:
  - catálogo com Notion conectado e Stripe por conectar;
  - "Outro servidor" com o campo de token expandido.
- O cadastro por header continua passando nos testes existentes.

## Fora do escopo
Linear e Atlassian no catálogo. Popup. Reaproveitar o DCR entre cliques.
