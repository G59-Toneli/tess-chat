# 28 — Navegação na sidebar, login demo direto, descrição de tool para o usuário

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 27
**Refs:** `docs/UX-AUDITORIA.md` (achados de severidade alta e média), `docs/UI-GUIA.md`, ADR 0013. Decisão do Toneli em 23/09.

**Referências visuais obrigatórias:** https://www.beautifului.dev/ e https://ui.shadcn.com/docs/components . Skill obrigatória: `/frontend-design:frontend-design`.

**What to build:**
1. **Navegação.** As 8 telas internas (Tools, Servidores MCP, Conectores, Créditos, Auditoria, Compartilhados, Configuração, Administração) saem do menu do avatar como único caminho e ganham um bloco de navegação no rodapé da sidebar, com ícone lucide e rótulo, estado ativo, Administração só para superuser. O menu do avatar mantém Perfil, Configuração e Sair. Agrupar se fizer sentido (ex.: "Extensões": Tools, MCP, Conectores; "Conta": Créditos, Auditoria, Compartilhados). Sidebar continua com a lista de conversas rolando; o bloco de navegação fica fixo embaixo.
2. **Login demo.** O botão "Entrar com conta demo" faz o login e redireciona. Manter o preenchimento visível por um instante não é necessário.
3. **Descrição para o usuário.** Coluna `descricao_usuario` em `tools` (migração `0016`), preenchida para todas as tools nativas, google e mcp (para MCP: usar a descrição do servidor, cortada em 140 caracteres). `GET /api/tools` e o estado da conversa devolvem `descricao_usuario`; o modelo continua recebendo `descricao`. `/tools` e o SeletorTools mostram `descricao_usuario`. Texto em pt-BR, voz do produto ("Busca na web e cita as fontes"), sem instrução ao modelo.

**Aceite:**
- [ ] Logado como não-admin: sidebar mostra 7 links, sem Administração. Como admin: 8. Screenshot dark `28-sidebar-nav.png` (admin) e `28-sidebar-nav-user.png`.
- [ ] Clique em "Entrar com conta demo" cai no chat logado.
- [ ] Teste: `GET /api/tools` devolve `descricao_usuario` sem a string "usuário" nem "NÃO" para `gmail_send`; o registro do modelo continua com a `descricao` original.
- [ ] `uv run pytest tests/test_tools.py tests/test_email.py tests/test_mcp.py` verde; `tsc` e `npm run build` limpos.
