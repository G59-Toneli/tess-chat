# 07a — Scaffold do front (sem integração com API)

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** —
**Refs:** ADR 0002. Spike hipótese 3 (`spike/RESULTADO.md` e `spike/web/` como referência do que funcionou).

**What to build:** `web/` com Vite + React + TypeScript, Tailwind, shadcn iniciado com `-b radix`, AI Elements (`conversation`, `message`, `prompt-input`, `response`, `sources`, `tool`, `reasoning`), `@ai-sdk/react`, react-router, `TooltipProvider` na raiz. Layout base em pt-BR: sidebar (lista de conversas, placeholder), área de chat, header com menu do usuário. Telas placeholder: `/login`, `/`, `/c/:id`, `/s/:shareId`, `/config`, `/auditoria`, `/creditos`, `/tools`, `/mcp`, `/conectores`. Nenhuma chamada real à API ainda: dados mock locais. `Dockerfile` multi-stage na raiz: stage 1 builda `web/`, stage 2 imagem Python com `api/` servindo `web/dist` como estático em `/` e a API em `/api` (o FastAPI de `api/app/main.py` ganha o mount de estáticos com fallback para `index.html` em rota não-API). Proxy de dev no Vite: `/api` → `http://localhost:8000`.

Não toque em `api/` além do mount de estáticos em `main.py` e da dependência necessária. Outro agente está editando `api/app/` para auth; se `main.py` conflitar no rebase, mantenha as duas alterações.

**Aceite:**
- [x] `npm run build` em `web/` sem erro e sem warning de tipo.
- [x] `docker build .` gera uma imagem que sobe e responde `/` (HTML do app) e `/health` (API).
- [x] Todas as rotas listadas renderizam um placeholder navegável.

## Answer
`web/` com Vite, React, Tailwind, shadcn radix-nova e AI Elements. Layout com sidebar mock, chat mock e menu do usuário. As 10 rotas estão navegáveis. Dark é o tema padrão, com toggle no menu (docs/UI-GUIA.md). O `Dockerfile` da raiz tem 2 stages. O FastAPI serve `web/dist` com fallback de SPA via `app/estaticos.py`. `/api/*` sem rota devolve 404.
Ressalvas: o `response` do AI Elements virou `MessageResponse`. O único aviso do build é o de chunk grande (streamdown, 1,5 MB), igual ao spike. O container precisa de `DATABASE_URL` por env, porque o `.env` fica fora da imagem. Screenshots em `.scratch/desafio/screens/07a-*.png`.
Sem `REVISAR(human)`: o ticket não tem `TODO(human)`.
