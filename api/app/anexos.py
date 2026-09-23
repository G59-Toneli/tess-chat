"""Anexos: upload, download e entrega ao modelo como BinaryContent (tickets 09 e 09b)."""

import base64
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic_ai.ui.vercel_ai.request_types import FileUIPart, UIMessage
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.auth import User, current_user
from app.config import settings
from app.conversas import Attachment
from app.db import get_session

LIMITE_BYTES = 20 * 1024 * 1024
EXTENSAO = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "application/pdf": ".pdf"}
# Gemini: PDF em resolução média por parte (research/02 §1.5). Imagem fica no default.
# O SDK do Google só aceita o objeto `{level}`; a string solta falha na validação do Part.
MEDIA_PDF = {"media_resolution": {"level": "MEDIA_RESOLUTION_MEDIUM"}}
RESOLUCAO_PDF = {"pydantic_ai": {"vendor_metadata": MEDIA_PDF}}
URL_ANEXO = re.compile(r"^/api/attachments/([0-9a-f-]{36})$")

Sessao = Annotated[AsyncSession, Depends(get_session)]
Usuario = Annotated[User, Depends(current_user)]

router = APIRouter(prefix="/api/attachments", tags=["anexos"])


# REVISAR(human): o tipo sai dos primeiros bytes, não do Content-Type do browser.
# Content-Type é declarado pelo cliente; um .txt renomeado para .png passaria.
def tipo_real(cabeca: bytes) -> str | None:
    """Tipo MIME pelos bytes mágicos. None se não é png/jpg/webp/pdf."""
    if cabeca.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if cabeca.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if cabeca[:4] == b"RIFF" and cabeca[8:12] == b"WEBP":
        return "image/webp"
    if cabeca.startswith(b"%PDF-"):
        return "application/pdf"
    return None


@router.post("", status_code=201)
async def enviar(file: UploadFile, session: Sessao, user: Usuario) -> dict:
    """Guarda o arquivo em disco e os metadados em `attachments`. Ainda sem Mensagem."""
    dados = await file.read(LIMITE_BYTES + 1)
    if len(dados) > LIMITE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima de 20 MB")
    mime = tipo_real(dados[:16])
    if mime is None:
        raise HTTPException(status_code=415, detail="Tipo não permitido. Envie PNG, JPG, WEBP ou PDF.")
    aid = uuid.uuid4()
    pasta = Path(settings.attachments_dir)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{aid}{EXTENSAO[mime]}"
    caminho.write_bytes(dados)
    anexo = Attachment(
        id=aid, user_id=user.id, filename=file.filename or caminho.name, mime_type=mime,
        size_bytes=len(dados), path=str(caminho),
    )
    session.add(anexo)
    await audit(
        session, "attachment_uploaded", user_id=user.id,
        payload={"attachment_id": str(aid), "mime_type": mime, "size_bytes": len(dados)},
    )
    await session.commit()
    return {
        "id": str(aid), "filename": anexo.filename, "mime_type": mime,
        "size_bytes": len(dados), "url": f"/api/attachments/{aid}",
    }


async def _do_usuario(session: AsyncSession, uid: uuid.UUID, aid: uuid.UUID) -> Attachment:
    """Anexo do Usuário. De outro ou inexistente: 404 igual."""
    anexo = await session.scalar(select(Attachment).where(Attachment.id == aid, Attachment.user_id == uid))
    if anexo is None:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    return anexo


@router.get("/{aid}")
async def baixar(aid: uuid.UUID, session: Sessao, user: Usuario) -> FileResponse:
    anexo = await _do_usuario(session, user.id, aid)
    return FileResponse(anexo.path, media_type=anexo.mime_type, filename=anexo.filename)


# REVISAR(human): só referência a anexo próprio vira arquivo para o modelo. Qualquer outra
# URL é 422: o Pydantic AI baixaria ela do servidor (SSRF). Os bytes entram como data URI,
# que o adapter converte em BinaryContent; o PDF leva media_resolution medium.
async def montar_anexos(session: AsyncSession, uid: uuid.UUID, nova: UIMessage) -> None:
    """Troca as referências `/api/attachments/{id}` da mensagem nova pelos bytes do arquivo."""
    for p in nova.parts:
        if not isinstance(p, FileUIPart):
            continue
        casou = URL_ANEXO.match(p.url)
        if casou is None:
            raise HTTPException(status_code=422, detail="Anexo precisa ser enviado por /api/attachments")
        anexo = await _do_usuario(session, uid, uuid.UUID(casou[1]))
        dados = base64.b64encode(Path(anexo.path).read_bytes()).decode()
        p.url = f"data:{anexo.mime_type};base64,{dados}"
        p.media_type = anexo.mime_type
        p.filename = anexo.filename
        if anexo.mime_type == "application/pdf":
            p.provider_metadata = RESOLUCAO_PDF


# REVISAR(human): bytes só no turno do anexo. Em turno anterior o modelo já respondeu sobre
# o arquivo e a resposta está no histórico; reenviar pesaria na reserva e no contexto todo turno.
# Todo arquivo vira texto, inclusive linhas antigas com data URI e URL externa (SSRF).
def sem_bytes(partes: list[dict]) -> list[dict]:
    """Partes de turno anterior com cada arquivo trocado por `[anexo: nome]`."""
    return [
        {"type": "text", "text": f"[anexo: {p.get('filename') or p.get('mediaType')}]"} if p.get("type") == "file" else p
        for p in partes
    ]


def partes_por_referencia(nova: UIMessage) -> list[dict]:
    """Partes da mensagem do front como chegaram: arquivo com url `/api/attachments/{id}`, sem bytes."""
    return [p.model_dump(mode="json", by_alias=True, exclude_none=True) for p in nova.parts]


async def ligar_a_mensagem(session: AsyncSession, uid: uuid.UUID, nova: UIMessage, message_id: int) -> list[str]:
    """Preenche `attachments.message_id` dos anexos citados. Devolve os ids ligados."""
    ids = [
        uuid.UUID(c[1]) for p in nova.parts if isinstance(p, FileUIPart) and (c := URL_ANEXO.match(p.url))
    ]
    if ids:
        await session.execute(
            update(Attachment).where(Attachment.id.in_(ids), Attachment.user_id == uid).values(message_id=message_id)
        )
    return [str(i) for i in ids]
