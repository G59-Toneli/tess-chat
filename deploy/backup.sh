#!/usr/bin/env bash
# Dump diário do Postgres. Mantém 7 dias para não encher o disco compartilhado.
set -euo pipefail
DEST=/opt/tess-chat/backups
mkdir -p "$DEST"
docker compose -f /opt/tess-chat/deploy/docker-compose.yml exec -T postgres \
  pg_dump -U tess_owner tess | gzip > "$DEST/tess-$(date +%F).sql.gz"
find "$DEST" -name 'tess-*.sql.gz' -mtime +7 -delete
