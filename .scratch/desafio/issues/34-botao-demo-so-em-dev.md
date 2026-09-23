# 34 — Botão "Entrar com conta demo" só em dev

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ticket 28 (login demo direto), `api/app/config.py` (`env`), `web/src/pages/Login.tsx`, `web/src/lib/api.ts`. Pedido do Toneli em 23/09 13:20 com produção no ar.

**What to build:** endpoint público `GET /api/config-publica` → `{ "demo": bool, "env": "dev"|"prod" }`, `demo = env != "prod"`. O Login lê esse endpoint ao montar e só renderiza o botão demo quando `demo` é true (sem piscar: renderiza o botão só depois da resposta). Em `ENV=prod` o endpoint `POST /auth/jwt/login` continua aceitando a conta demo (o CPO usa), só o atalho some. Decisão em tempo de execução, não em build, para a mesma imagem Docker servir dev e prod (registrar em DECISOES-AUTONOMAS). Atualizar `.env.example` e `docs/INFRA.md` (1 linha cada).

**Aceite:**
- [x] Teste: com `ENV=prod` o endpoint devolve `demo=false`; com `dev`, `true`.
- [x] Screenshot dark do login sem o botão (`34-login-prod.png`) obtido com a API em `ENV=prod` numa porta própria.
- [x] `tsc`, `npm run build`, `uv run pytest tests/test_auth.py` (ou onde couber) verdes.

## Answer
- `GET /api/config-publica` em `main.py` devolve `{demo, env}`, com `demo = env != "prod"`. Decisão em runtime (DECISOES-AUTONOMAS).
- O Login lê o endpoint ao montar. O botão só aparece depois da resposta com `demo=true`. Erro na leitura esconde o botão.
- 3 testes novos em `test_auth.py`: prod devolve false, dev devolve true, login demo segue aceito em prod.
- Ressalva: produção só esconde o botão se o `.env` do VPS tiver `ENV=prod`. Não conferido daqui.
- Sem REVISAR(human).
