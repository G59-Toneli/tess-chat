"""Varredura diária de arquivos de anexo órfãos (ticket 50).

Uso: `python -m app.limpeza_anexos [--dry-run]`. O cron do VPS roda uma vez por dia.
"""

import argparse
import asyncio
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.config import settings
from app.conversas import Attachment
from app.db import SessionLocal

ABANDONO = timedelta(hours=24)
# Upload em andamento: o arquivo é gravado antes da linha. Mais novo que isso nunca sai.
CARENCIA_S = 3600


# varredura em vez de hook em cada exclusão. O cascade apaga a linha no banco
# sem o código ver; a varredura pega qualquer caminho, inclusive exclusão manual. Ordem:
# 1) linhas de upload abandonado (sem Mensagem há 24 h) saem primeiro; 2) todo arquivo de
# `attachments_dir` sem linha e com mais de 1 h sai. Só olha o primeiro nível da pasta e
# pula symlink e subpasta, então nunca apaga fora dela.
async def varrer(session: AsyncSession, dry_run: bool = False) -> dict:
    """Apaga arquivo sem linha e upload abandonado. Devolve contagens; `dry_run` só lista."""
    corte = datetime.now(UTC) - ABANDONO
    abandonado = (Attachment.message_id.is_(None)) & (Attachment.created_at < corte)
    if dry_run:
        abandonados = list(await session.scalars(select(Attachment.id).where(abandonado)))
        vivos = await session.scalars(select(Attachment.path).where(~abandonado))
    else:
        abandonados = list(await session.scalars(delete(Attachment).where(abandonado).returning(Attachment.id)))
        # Linha sai antes do arquivo: se cair no meio, sobra só arquivo órfão para amanhã.
        await session.commit()
        vivos = await session.scalars(select(Attachment.path))
    com_linha = {os.path.normcase(os.path.abspath(p)) for p in vivos}

    pasta = Path(settings.attachments_dir)
    limite = time.time() - CARENCIA_S
    apagados: list[str] = []
    liberados = 0
    if pasta.is_dir():
        with os.scandir(pasta) as itens:
            for item in itens:
                if not item.is_file(follow_symlinks=False):
                    continue
                info = item.stat(follow_symlinks=False)
                if info.st_mtime > limite or os.path.normcase(os.path.abspath(item.path)) in com_linha:
                    continue
                if not dry_run:
                    os.unlink(item.path)
                apagados.append(item.path)
                liberados += info.st_size

    resultado = {"files_deleted": len(apagados), "rows_deleted": len(abandonados), "bytes_freed": liberados}
    if not dry_run:
        await audit(session, "attachments_swept", payload=resultado)
        await session.commit()
    return {**resultado, "files": apagados}


async def _main(dry_run: bool) -> None:
    async with SessionLocal() as session:
        r = await varrer(session, dry_run=dry_run)
    for f in r["files"]:
        print(("[dry-run] " if dry_run else "") + f)
    print(f"arquivos={r['files_deleted']} linhas={r['rows_deleted']} bytes={r['bytes_freed']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Limpeza de arquivos de anexo órfãos.")
    p.add_argument("--dry-run", action="store_true", help="só lista, não apaga nem grava evento")
    asyncio.run(_main(p.parse_args().dry_run))
