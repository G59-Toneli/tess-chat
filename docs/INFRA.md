# Infra de produção

ADR 0014. URL: https://chat.toneli.dev.br

## Inventário do VPS (23/09/2026)
- Oracle, São Paulo. `aarch64`, Ubuntu 24.04, 4 OCPU, 24 GB. Disco `/` de 96 GB.
- Acesso: `ssh -i <chave> ubuntu@<ip-do-vps>`. Sudo sem senha. Regras em `<arquivo-de-acesso>`.
- É o VPS compartilhado. Outros projetos: outro projeto-hub (outro projeto, 127.0.0.1:3100), outro projeto-orchestrator (127.0.0.1:8000), cdt-erpnext (127.0.0.1:8081), cloudflared (127.0.0.1:20241).
- Nginx no host em 80/443 com certbot. `outro projeto-hub` é `default_server` em 80 e 443.
- Portas em uso antes do deploy: 22 53 80 111 443 3100 8000 8081 20241.

## O que é nosso
| Item | Onde |
|---|---|
| Código e compose | `/opt/tess-chat` (compose em `deploy/docker-compose.yml`, projeto `tess-chat`) |
| Segredos | `/opt/tess-chat/.env` (modo 600, fora do git) |
| App | `127.0.0.1:8010` |
| Volumes | `tess-chat_pgdata`, `tess-chat_appdata` (anexos) |
| Site nginx | `/etc/nginx/sites-available/tess-chat` + symlink em `sites-enabled` |
| Backup | `/etc/cron.d/tess-chat`, dumps em `/opt/tess-chat/backups` (7 dias) |
| Deploy key | `~/.ssh/tess-deploy`, alias ssh `github-tess` em `~/.ssh/config` |
| Commit no ar | `/opt/tess-chat/DEPLOYED_COMMIT` enquanto não há `.git`; depois `git rev-parse HEAD` |

## Regras
- Sempre `docker compose -f deploy/docker-compose.yml`. O compose da raiz é de dev e publica 5433 e 8765.
- Antes de buildar: `df -h /`. Acima de 90%, pare.
- Limpeza: `docker image prune -f`. Nunca `-a`, nunca `docker builder prune`.
- Não toque em serviço, container, site ou diretório que não esteja na tabela acima.

## Runbook
Todos os comandos rodam em `/opt/tess-chat` no VPS.

**Deploy (CI ou manual):**
```
bash /opt/tess-chat/deploy/deploy.sh
```
O script faz `git pull --ff-only` (se houver `.git`), confere o disco, `up -d --build` e `image prune -f`. O serviço `migrate` roda `alembic upgrade head` antes do app.

**Deploy manual sem git no VPS (até a deploy key existir), a partir da máquina local:**
```
git -c core.autocrlf=false archive HEAD | ssh -i <chave> ubuntu@<ip-do-vps> 'tar -x -C /opt/tess-chat'
ssh -i <chave> ubuntu@<ip-do-vps> 'bash /opt/tess-chat/deploy/deploy.sh'
```
Grave o hash em `DEPLOYED_COMMIT`.

**Ligar o git no VPS (depois de cadastrar a deploy key no GitHub):**
```
cd /opt/tess-chat
git init -b main
git remote add origin git@github-tess:G59-Toneli/tess-chat.git
git fetch origin main
git reset --hard origin/main
rm -f DEPLOYED_COMMIT
```
O `reset --hard` não apaga `.env`, `backups/` nem `build.log`: não estão no git.

**Logs:**
```
docker compose -f deploy/docker-compose.yml logs -f app
docker compose -f deploy/docker-compose.yml logs migrate
```

**Backup manual e restauração:**
```
./deploy/backup.sh
gunzip -c backups/tess-AAAA-MM-DD.sql.gz | docker compose -f deploy/docker-compose.yml exec -T postgres psql -U tess_owner tess
```
Restaurar em cima de banco com dados dá conflito. Para restaurar limpo: `down`, `docker volume rm tess-chat_pgdata`, `up -d postgres --wait`, restaurar, `up -d`.

**Rollback:**
```
git reset --hard <hash-anterior>
docker compose -f deploy/docker-compose.yml up -d --build
```
Migração não volta sozinha. Se o commit ruim trouxe migração, rode `docker compose -f deploy/docker-compose.yml run --rm migrate alembic downgrade <rev>` antes.

**Remover tudo:**
```
docker compose -f deploy/docker-compose.yml down -v --rmi local
sudo rm /etc/nginx/sites-enabled/tess-chat /etc/nginx/sites-available/tess-chat /etc/cron.d/tess-chat
sudo nginx -t && sudo systemctl reload nginx
sudo rm -rf /opt/tess-chat
```
O certificado fica em `/etc/letsencrypt`. Remova com `sudo certbot delete --cert-name chat.toneli.dev.br`.

## CI
`.github/workflows/deploy.yml`: push na `main` faz ssh no VPS e roda `deploy/deploy.sh`. Secrets no GitHub: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
