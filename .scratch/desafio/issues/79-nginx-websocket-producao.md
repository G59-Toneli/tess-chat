# 79 — nginx de produção repassa o WebSocket da Ligação

**Type:** task (deploy/ + VPS)
**Status:** blocked
**Blocked by:** 76
**Refs:** ADR 0014, 0026. `docs/INFRA.md`. Regras da VM em `<arquivo-de-acesso>` (ler antes de qualquer comando). Autorizado pelo Toneli em 28/09 (Q30, opção a).

**Objetivo:** `wss://chat.toneli.dev.br/api/voz/ws` chega ao app com upgrade.

## Escopo
Este ticket PODE tocar `deploy/` e o VPS.
1. `deploy/nginx-tess-chat.conf`: um `location /api/voz/ws` com `proxy_http_version 1.1`, `Upgrade $http_upgrade`, `Connection "upgrade"`, `proxy_read_timeout` acima de 540 s. Nada mais muda no arquivo.
2. No VPS, só o site `tess-chat`: backup datado do arquivo atual, aplicar, `sudo nginx -t`. Falhou: restaurar o backup e não dar reload. Passou: `sudo systemctl reload nginx`. Nunca tocar no site do outro projeto.
3. `GEMINI_LIVE_API_KEY` no `.env` do VPS (`/opt/tess-chat`) e repassada no `deploy/docker-compose.yml`. Valor: a chave que o spike (75) validou.
4. `docs/INFRA.md`: runbook de 5 linhas desse passo.

## Aceite
- Com o 76 em produção: um cliente WS (script local) em `wss://chat.toneli.dev.br/api/voz/ws?ticket=invalido` recebe close `4401`, e não 400/502 do nginx. Isso prova que o upgrade passa sem gastar Gemini.
- Comandos, saída do `nginx -t` e caminho do backup no LEDGER.
- Chamadas reais: 0.

## Paradas de estudo
1 a 2 entradas no formato do `docs/ESTUDO-VOZ.md`. Obrigatória: o que é o upgrade de HTTP para WebSocket e por que o nginx descartava.
