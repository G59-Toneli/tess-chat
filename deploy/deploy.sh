#!/usr/bin/env bash
# Atualiza o código e sobe a stack. Usado pelo CI e pelo deploy manual.
set -euo pipefail
cd /opt/tess-chat
if [ -d .git ]; then git pull --ff-only origin main; fi
df -h / | awk 'NR==2 { gsub("%","",$5); if ($5+0 > 90) { print "disco acima de 90%, abortando"; exit 1 } }'
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build
# Remove só imagens sem tag. Nunca -a (apaga rollback de outros projetos).
docker image prune -f
docker compose -f deploy/docker-compose.yml ps
