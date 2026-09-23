# 07 — Front base: login, lista de conversas, chat streaming

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** 06
**Refs:** ADR 0002. `docs/UI-GUIA.md` (obrigatório). Resultado do spike (hipótese 3).

**What to build:** `web/` com Vite + React + shadcn + AI Elements (ou fallback do spike). Telas: login/cadastro, sidebar de conversas, chat com `useChat`. Build copiado para o container do FastAPI e servido em `/`. UI em pt-BR.

**Aceite:**
- [ ] Fluxo completo no browser: cadastrar, criar conversa, mandar mensagem, ver stream, recarregar e ver histórico.
- [ ] `docker build` gera uma imagem só que serve front e API.

**Do spike:** `shadcn init -b radix` (Base UI quebra o `prompt-input`). Sem `baseUrl` no tsconfig (TS 6). Envolver o app em `TooltipProvider`. Code-split só se o bundle de 1,6 MB incomodar.

**Acabamento obrigatório (revisão do orquestrador nas telas do 07a):** o scaffold está funcional mas cru. Neste ticket: nome do app "Tess Chat" com ícone no header e no login; login em card centralizado com título, subtítulo, alternar cadastro, botão "entrar com conta demo" que preenche as credenciais; sidebar com avatar/iniciais, busca, agrupamento por data (hoje, ontem, 7 dias), menu por conversa (renomear, apagar com confirmação); área de chat vazia com estado "comece uma conversa" e 3 sugestões clicáveis; indicador de "pensando" antes do primeiro token; mensagens com avatar e horário; erro do provedor como toast em pt-BR. Seguir `docs/UI-GUIA.md` e olhar https://www.beautifului.dev/ para loading e "digitando". Screenshots dark de login, lista vazia, conversa com stream e erro.
