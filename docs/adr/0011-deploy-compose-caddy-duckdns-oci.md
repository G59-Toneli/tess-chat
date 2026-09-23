# ADR 0011 — Deploy em Docker Compose com Caddy e domínio próprio no VPS OCI

**Status:** aceito, 2026-09-23. **Substituído em parte pelo [ADR 0014](0014-deploy-nginx-do-host-no-vps-compartilhado.md):** sem Caddy e sem OCI; o deploy roda atrás do nginx do host, no VPS compartilhado. Compose, CI por ssh e domínio ficam (seção "O que fica igual" do 0014).

## Decisão
Compose com `caddy`, `app`, `postgres`. HTTPS automático via Caddy. Domínio próprio `toneli.dev.br` (adquirido em 23/09), subdomínio `chat.toneli.dev.br` com registro A para o IP do VPS. DuckDNS era o plano se não houvesse domínio. Descartados: Cloudflare Quick Tunnel (não passa SSE, mata streaming), ngrok (URL efêmera, interstitial), Coolify e Dokploy (2 GB de RAM e horas de setup). Portas 80 e 443 abertas na Security List **e** no iptables. Se o VPS for aarch64, build da imagem no próprio VPS. CI: GitHub Actions com ssh para `docker compose up -d --build`.

## Consequências
- Hello-world atrás do Caddy sobe no dia 2 (ticket 02), para queimar os riscos de rede cedo.
- Redirect URI do Google: `https://chat.toneli.dev.br/api/connectors/google/callback`.
