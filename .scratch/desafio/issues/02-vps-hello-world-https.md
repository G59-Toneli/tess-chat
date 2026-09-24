# 02 — VPS: hello-world atrás de Caddy com HTTPS

**Type:** task (HITL + AFK)
**Status:** resolved (substituído pelo ADR 0014: VPS compartilhado com nginx do host, não OCI com Caddy)
**Blocked by:** —
**Refs:** ADR 0011. `research/03` §4.

**What to build:** o VPS OCI servindo uma página estática em `https://chat.toneli.dev.br` via Docker Compose com `caddy`. Usar `mattpocock-skills:wizard` para as etapas que só Toneli faz.

**HITL (Toneli):** criar registro A `chat.toneli.dev.br` apontando pro IP público do VPS, no painel DNS do domínio; abrir 80/443 na Security List da VCN; passar acesso SSH ao agente ou rodar o wizard.
**AFK (agente):** no VPS: `nproc`, `free -h`, `uname -m`, `df -h` gravados em `docs/INFRA.md`; abrir 80/443 no iptables; instalar Docker se faltar; compose com caddy + página; Caddyfile mínimo.

**Aceite:**
- [ ] `curl -I https://chat.toneli.dev.br` devolve 200 com certificado válido.
- [ ] `docs/INFRA.md` tem CPU, RAM, arquitetura e disco reais do VPS.
- [ ] Compose e Caddyfile commitados em `deploy/`.

## Answer

Fechado em 24/09 sem executar como escrito. A conta OCI falhou e o deploy foi para o VPS compartilhado, onde o nginx do host já ocupa 80/443 (ADR 0014). Produção no ar em https://chat.toneli.dev.br com HTTPS e CI desde 23/09 (ticket 16).
