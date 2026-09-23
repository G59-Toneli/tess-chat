# 07 — Front base: login, lista de conversas, chat streaming

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 06
**Refs:** ADR 0002. `docs/UI-GUIA.md` (obrigatório). Resultado do spike (hipótese 3).

**What to build:** `web/` com Vite + React + shadcn + AI Elements (ou fallback do spike). Telas: login/cadastro, sidebar de conversas, chat com `useChat`. Build copiado para o container do FastAPI e servido em `/`. UI em pt-BR.

**Aceite:**
- [ ] Fluxo completo no browser: cadastrar, criar conversa, mandar mensagem, ver stream, recarregar e ver histórico.
- [ ] `docker build` gera uma imagem só que serve front e API.

**Do spike:** `shadcn init -b radix` (Base UI quebra o `prompt-input`). Sem `baseUrl` no tsconfig (TS 6). Envolver o app em `TooltipProvider`. Code-split só se o bundle de 1,6 MB incomodar.
