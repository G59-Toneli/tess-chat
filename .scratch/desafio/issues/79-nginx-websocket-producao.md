# 79 — nginx de produção repassa o WebSocket da Ligação

**Type:** task (deploy/ + VPS)
**Status:** resolved
**Blocked by:** 76
**Refs:** ADR 0014, 0026. `docs/INFRA.md`. Regras da VM em o arquivo de acesso (ler antes de qualquer comando). Autorizado pelo Toneli em 28/09 (Q30, opção a).

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

## Answer
Location `/api/voz/ws` em `deploy/nginx-tess-chat.conf` e no site `tess-chat` do VPS (backup `/etc/nginx/sites-available/tess-chat.bak-20260929-095122`, `nginx -t` ok, reload ok). `GEMINI_LIVE_API_KEY` acrescentada ao `.env` de `/opt/tess-chat` com o valor de `GEMINI_API_KEY`; nenhuma outra linha mudou. O compose já repassa pelo `env_file`, sem edição. O app foi recriado pelo deploy do CI e o container tem a variável. Aceite: cliente WS em `wss://chat.toneli.dev.br/api/voz/ws?ticket=invalido` abriu e recebeu close 4401; curl com upgrade deu 101. Nada `REVISAR(human)`.

## Paradas de estudo

### 1. Upgrade de HTTP para WebSocket
- **Conceito:** WebSocket começa como um GET HTTP com `Upgrade: websocket` e `Connection: Upgrade`. O servidor responde `101 Switching Protocols` e a mesma conexão TCP vira um canal aberto nos dois sentidos.
- **Por quê:** `Upgrade` e `Connection` são headers hop-by-hop: o nginx não repassa. Ele ainda fala HTTP/1.0 com o backend por padrão e zera `Connection` com o nosso `proxy_set_header Connection ""`. O backend nunca via o upgrade e respondia 400 ou 502. A location dedicada põe `proxy_http_version 1.1`, `Upgrade $http_upgrade` e `Connection "upgrade"`. Repetimos os outros `proxy_set_header` nela, porque declarar um só na location descarta os herdados do server. Alternativa que caiu: mudar o `Connection ""` global, que afetaria SSE e o resto do site.
- **Onde:** `deploy/nginx-tess-chat.conf`, `location /api/voz/ws`.
- **Pergunta de revisão:** "Por que o WebSocket não passava pelo nginx?"
  **Resposta:** O upgrade é um handshake HTTP com headers hop-by-hop, e o nginx não os repassa sozinho. Eu declarei `Upgrade` e `Connection "upgrade"` numa location só da Ligação, com HTTP 1.1 e timeout de leitura de 600 s. O resto do site ficou como estava.

### 2. Provar o upgrade sem gastar Gemini
- **Conceito:** um ticket inválido faz o app aceitar o WebSocket e fechar com código 4401.
- **Por quê:** close 4401 vindo do app prova que o handshake atravessou o nginx. Se o nginx barrasse, viria 400 ou 502. Alternativa que caiu: abrir uma Ligação real, que gasta cota Gemini.
- **Onde:** `api/app/voz.py`, rota `/api/voz/ws`.
- **Pergunta de revisão:** "Como você testou a infra sem custo?"
  **Resposta:** Mandei um ticket inválido. O app fecha com 4401 antes de falar com o Gemini. Ver o 4401 prova que o upgrade passou.
