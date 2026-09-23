# 02 — VPS: hello-world atrás de Caddy com HTTPS

**Type:** task (HITL + AFK)
**Status:** ready-for-agent
**Blocked by:** —
**Refs:** ADR 0011. `research/03` §4.

**What to build:** o VPS OCI servindo uma página estática em `https://chat.toneli.dev.br` via Docker Compose com `caddy`. Usar `mattpocock-skills:wizard` para as etapas que só Toneli faz.

**HITL (Toneli):** criar registro A `chat.toneli.dev.br` apontando pro IP público do VPS, no painel DNS do domínio; abrir 80/443 na Security List da VCN; passar acesso SSH ao agente ou rodar o wizard.
**AFK (agente):** no VPS: `nproc`, `free -h`, `uname -m`, `df -h` gravados em `docs/INFRA.md`; abrir 80/443 no iptables; instalar Docker se faltar; compose com caddy + página; Caddyfile mínimo.

**Aceite:**
- [ ] `curl -I https://chat.toneli.dev.br` devolve 200 com certificado válido.
- [ ] `docs/INFRA.md` tem CPU, RAM, arquitetura e disco reais do VPS.
- [ ] Compose e Caddyfile commitados em `deploy/`.
