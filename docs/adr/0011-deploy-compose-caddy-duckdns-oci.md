# ADR 0011 — Deploy em Docker Compose com Caddy e DuckDNS no VPS OCI

**Status:** aceito, 2026-09-23

## Decisão
Compose com `caddy`, `app`, `postgres`. HTTPS automático via Caddy. Domínio em `duckdns.org`: grátis, está na Public Suffix List (cota própria no Let's Encrypt) e vale como redirect URI do Google. Descartados: Cloudflare Quick Tunnel (não passa SSE, mata streaming), ngrok (URL efêmera, interstitial), Coolify e Dokploy (2 GB de RAM e horas de setup). Portas 80 e 443 abertas na Security List **e** no iptables. Se o VPS for aarch64, build da imagem no próprio VPS. CI: GitHub Actions com ssh para `docker compose up -d --build`.

## Consequências
- Hello-world atrás do Caddy sobe no dia 2 (ticket 02), para queimar os riscos de rede cedo.
- Se Toneli comprar domínio, troca só o Caddyfile.
