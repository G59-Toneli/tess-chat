# 07a — Scaffold do front (sem integração com API)

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** —
**Refs:** ADR 0002. Spike hipótese 3 (`spike/RESULTADO.md` e `spike/web/` como referência do que funcionou).

**What to build:** `web/` com Vite + React + TypeScript, Tailwind, shadcn iniciado com `-b radix`, AI Elements (`conversation`, `message`, `prompt-input`, `response`, `sources`, `tool`, `reasoning`), `@ai-sdk/react`, react-router, `TooltipProvider` na raiz. Layout base em pt-BR: sidebar (lista de conversas, placeholder), área de chat, header com menu do usuário. Telas placeholder: `/login`, `/`, `/c/:id`, `/s/:shareId`, `/config`, `/auditoria`, `/creditos`, `/tools`, `/mcp`, `/conectores`. Nenhuma chamada real à API ainda: dados mock locais. `Dockerfile` multi-stage na raiz: stage 1 builda `web/`, stage 2 imagem Python com `api/` servindo `web/dist` como estático em `/` e a API em `/api` (o FastAPI de `api/app/main.py` ganha o mount de estáticos com fallback para `index.html` em rota não-API). Proxy de dev no Vite: `/api` → `http://localhost:8000`.

Não toque em `api/` além do mount de estáticos em `main.py` e da dependência necessária. Outro agente está editando `api/app/` para auth; se `main.py` conflitar no rebase, mantenha as duas alterações.

**Aceite:**
- [ ] `npm run build` em `web/` sem erro e sem warning de tipo.
- [ ] `docker build .` gera uma imagem que sobe e responde `/` (HTML do app) e `/health` (API).
- [ ] Todas as rotas listadas renderizam um placeholder navegável.
