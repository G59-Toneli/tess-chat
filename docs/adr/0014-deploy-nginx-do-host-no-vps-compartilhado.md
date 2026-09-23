# ADR 0014 — Deploy atrás do nginx do host, no VPS compartilhado

**Status:** aceito, 2026-09-23. Substitui a parte "Caddy" do ADR 0011.

## Contexto
A conta OCI nova falhou. O deploy vai para o VPS do trabalho do Toneli (aarch64, Ubuntu 24.04), que já roda outro projeto em produção. Esse VPS tem nginx no host em 80/443, com certbot gerenciando os certificados.

## Decisão
- Sem Caddy. Um Caddy nosso precisaria das portas 80/443, que são do nginx do host. Parar ou trocar o nginx derruba a produção do outro projeto.
- O nginx do host ganha um site novo, `/etc/nginx/sites-available/tess-chat` (fonte em `deploy/nginx-tess-chat.conf`), com proxy para `127.0.0.1:8010`. Sites existentes não mudam.
- SSE passa porque o site tem `proxy_buffering off` e `proxy_read_timeout 3600`.
- TLS: `certbot --nginx -d chat.toneli.dev.br`, a mesma ferramenta que o VPS já usa.
- O compose (`deploy/docker-compose.yml`) fica com `postgres`, `migrate` e `app`. O Postgres não publica porta. O app publica só em `127.0.0.1:8010`.
- `migrate` roda `alembic upgrade head` e sai. O app depende dele porque o seed da conta demo precisa das tabelas.
- A senha do papel `tess_app` continua a do `docker/postgres-init`. O banco só é visível na rede interna do compose. A senha do dono (`tess_owner`) é própria da produção.

## O que fica igual ao ADR 0011
Compose como unidade de deploy. Imagem buildada no próprio VPS (arm64). CI com GitHub Actions por ssh. Domínio `chat.toneli.dev.br`. Backup diário do Postgres por cron.

## Consequências
- Tudo nosso sai com `docker compose -f deploy/docker-compose.yml down -v`, mais o site nginx, `/etc/cron.d/tess-chat` e `/opt/tess-chat`.
- O certificado depende do certbot do host, não do nosso compose. Renovação vem do timer do certbot que já existe.
- Upload vai até 20 MB. O site precisa de `client_max_body_size 25M`, porque o default do nginx é 1 MB.
