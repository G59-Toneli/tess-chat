# 16 — Deploy da Camada 1 no VPS com CI

**Type:** task (AFK + HITL)
**Status:** resolved (parte AFK; DNS, TLS e secrets do CI no MANHA)
**Blocked by:** nenhum (02 absorvido por este ticket; 09 a 15 resolvidos)
**Refs:** ADR 0011. **Marco: sexta 26/09.**

**What to build:** `deploy/docker-compose.yml` com caddy, app, postgres, volumes persistentes. `.env` no VPS. GitHub Actions: em push na `main`, ssh no VPS, `git pull`, `docker compose up -d --build`, `alembic upgrade head`. Backup diário do Postgres por cron simples.

**HITL:** segredos no GitHub e no VPS.

**Aceite:**
- [x] Fluxo completo funciona no link público, em janela anônima. (HTTPS válido desde 23/09 ~13:05 -03; redeploy do HEAD 42cca64 pelo orquestrador; smoke test: root 200, login demo 200)
- [ ] Push na main atualiza o VPS sem intervenção.
- [ ] Reiniciar o VPS mantém dados.

**Contexto do VPS (23/09, noite):** conta OCI nova falhou. Deploy temporário no VPS Always Free do trabalho do Toneli, que já roda outro projeto. Chaves SSH chegam dia 24 de manhã. Antes de qualquer alteração: inventariar o que roda (`docker ps`, `ss -tlnp`, proxy existente em 80/443). Nunca parar nem alterar serviço existente. Se houver proxy, adicionar o host `chat.toneli.dev.br` nele. Se não houver, subir o Caddy nosso. Tudo do nosso lado em um único `docker compose` em `/opt/tess-chat`, removível com `down -v`.

**Acesso e inventário (23/09 ~13:40, feito pelo orquestrador):**
- Chave: `<omitido>` (cópia de `<omitido>`). `ssh -i <omitido> <omitido>@<omitido>`. Sudo sem senha. Regras da VM em `<omitido>` (leia inteiro antes de qualquer comando).
- `aarch64`, Ubuntu 24.04, 4 OCPU, 24 GB. Disco `/` 96G, 76G usados (80%). Rodar `df -h /` antes de buildar; `docker image prune -f` sem `-a`; nunca `docker builder prune`.
- Portas em uso: 22 53 80 111 443 3100 8000 8081 20241. Nginx no host em 80/443 com certbot. Escolher porta livre alta (ex. 8010) só em 127.0.0.1 e criar site novo em `/etc/nginx/sites-available/tess-chat` com proxy para `127.0.0.1:<porta>`, `proxy_buffering off` e `proxy_read_timeout 3600` para o SSE. Não editar sites existentes.
- Isso contraria o ADR 0011 (Caddy). Escrever `docs/adr/0014-deploy-nginx-do-host-no-vps-compartilhado.md`: VPS compartilhado já tem nginx+certbot em 80/443; Caddy nosso não pode tomar as portas; compose fica só com app + postgres em rede interna, publicando a porta do app em 127.0.0.1. Registrar por quê e o que fica igual (compose, CI, backup).
- DNS: `chat.toneli.dev.br` ainda NÃO resolve (13:40). Toneli está criando o registro A para <omitido>. Fazer tudo até o certbot; para o certbot, esperar o DNS com `dig +short chat.toneli.dev.br @8.8.8.8` em laço (até 30 min). Enquanto não resolve, validar por `curl -H "Host: chat.toneli.dev.br" http://127.0.0.1` dentro da VM.
- `.env` de produção: gerar `JWT_SECRET`, `CONNECTORS_KEY`, `DEMO_PASSWORD` novos; `ENV=prod`; `PUBLIC_BASE_URL=https://chat.toneli.dev.br`; copiar `GEMINI_PAID_API_KEY`, `TYPESAFE_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` do `.env` local; NÃO copiar `GITHUB_PAT`. Postgres do compose com senha própria, sem publicar porta.
- CI: GitHub Actions com `appleboy/ssh-action` (ou ssh puro) usando secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`. Escrever o workflow e listar em `MANHA.md` os secrets que o Toneli cadastra no GitHub (não cadastre você; o `GITHUB_PAT` está vazado). Até então, deploy manual por ssh documentado em `docs/INFRA.md`.
- Repo é privado: o `git pull` no VPS precisa de deploy key. Gerar par no VPS (`ssh-keygen -t ed25519 -f ~/.ssh/tess-deploy`), imprimir a pública no relatório e no `MANHA.md` para o Toneli cadastrar como Deploy Key (read-only) no GitHub. Até lá, copiar o código por `rsync`/`scp` a partir do working tree local (`git archive HEAD`).
- `docs/INFRA.md` ganha o inventário real acima e o runbook (deploy, logs, backup, rollback, `down -v`).

## Answer
- No ar no VPS: código fb9856e em `/opt/tess-chat`, compose `tess-chat` (postgres sem porta, `migrate`, app em 127.0.0.1:8010), site nginx `tess-chat` (80), backup diário em `/etc/cron.d/tess-chat`. Validado dentro da VM via `Host: chat.toneli.dev.br`: index 200, login demo devolve token, `down`+`up` mantém usuários e auditoria, backup gerou dump. ADR 0014 e runbook em `docs/INFRA.md`.
- Pendente (HITL): registro A `chat.toneli.dev.br` dá NXDOMAIN no autoritativo após 30 min de espera, então certbot não rodou e não há HTTPS. Depois do DNS: `sudo certbot --nginx -d chat.toneli.dev.br --non-interactive --agree-tos --redirect`.
- Pendente (HITL): deploy key, secrets do Actions e redirect do Google, passo a passo no `MANHA.md`. CI escrito, não executado.
- Ressalvas: sem smoke test de chat (todo turno chama o Jev, teto 0). Reboot real do VPS não testado (produção do trabalho). `DEMO_PASSWORD` segue `demo12345` (DECISOES).

