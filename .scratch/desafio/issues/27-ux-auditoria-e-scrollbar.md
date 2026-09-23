# 27 — Scrollbar do chat e auditoria de UX do app inteiro

**Type:** task (AFK, só web/)
**Status:** resolved
**Blocked by:** 26
**Refs:** `docs/UI-GUIA.md`, `CONTEXT.md`. Pedido do Toneli em 23/09 de manhã.

**Parte 1 — Scrollbar.** A área de mensagens do chat mostra a scrollbar nativa do sistema, sem estilo. Estilizar toda scrollbar do app (chat, sidebar, popover de tools, páginas internas): fina (6 a 8 px), trilho transparente, polegar com a cor de borda do tema, arredondado, some quando não está em hover onde fizer sentido. `scrollbar-width: thin` + `::-webkit-scrollbar` no CSS global. Dark e light.

**Parte 2 — Auditoria de UX, rigorosa.** Percorrer o app inteiro logado como demo (e como não-admin) e avaliar, tela a tela: a tela está no lugar certo do nav? o nome diz o que ela faz? o fluxo principal se completa sem ler doc? há estado vazio, carregando e erro em cada lista? o feedback de ação (salvar, toggle, enviar) é visível? labels e textos em pt-BR consistentes com o `CONTEXT.md`? hierarquia visual (título, descrição, ação primária) igual entre telas? foco e teclado no input do chat e nos diálogos? responsividade mínima em 1280 px? Telas: login, chat (novo e com histórico, com anexo, com tool, com rascunho de e-mail, com compactação), `/config`, `/tools`, `/mcp`, `/conectores`, `/creditos`, `/auditoria`, `/compartilhados`, share público, `/admin`.

**Regras:** corrigir na hora o que for local e claro (texto, espaçamento, ordem no nav, estado vazio, feedback). O que for mudança de fluxo ou de arquitetura de informação, NÃO fazer: listar em `docs/UX-AUDITORIA.md` com severidade, tela, problema, proposta. Registrar também o que foi corrigido. Zero mudança em `api/`.

**Aceite:**
- [ ] Scrollbar estilizada no chat e na sidebar. Screenshot `27-scrollbar.png` com conteúdo rolável visível.
- [ ] `docs/UX-AUDITORIA.md` cobre todas as telas listadas, com "corrigido" ou "proposta" em cada achado.
- [ ] Screenshots antes/depois de cada correção visual relevante em `.scratch/desafio/screens/27-*.png`.
- [ ] `tsc --noEmit` e `npm run build` limpos.

## Answer
- Parte 1: scrollbar global de 8 px, sem trilho e sem setas, polegar só no hover da área rolável (variável CSS, porque o Chromium não repinta `:hover::-webkit-scrollbar-thumb`). Polegar em `muted-foreground` 50%, não na borda: no dark a borda some. Screenshots `27-scrollbar*.png` (antes, dark, light, sidebar, popover).
- Parte 2: `docs/UX-AUDITORIA.md` com 27 achados em todas as telas pedidas: 14 corrigidos (foco no input, 404, Perfil fora do menu, erro da sidebar, textos de Tools, Conectores e Roteador, filtros da Auditoria a 1280 px, MCP) e 13 propostas.
- Propostas altas: navegação escondida no menu do avatar; botão demo que só preenche.
- Ressalva: compactação não verificada visualmente (sem Resumo acessível no banco de dev). Estados de erro das páginas internas vieram dos tickets 13 a 17, não foram simulados aqui.
- Nada em `api/`. Nenhum `REVISAR(human)` novo.
