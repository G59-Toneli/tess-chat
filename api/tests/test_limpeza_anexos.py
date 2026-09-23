"""Varredura diária de arquivos de anexo órfãos (ticket 50)."""

import os
import time
import uuid
from datetime import timedelta

import pytest
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import update

from app.chat import MODELO, modelo
from app.config import settings
from app.conversas import Attachment
from app.db import SessionLocal
from app.limpeza_anexos import varrer
from app.main import app
from tests.test_anexos import PNG, corpo, parte, subir
from tests.test_auth import eventos
from tests.test_conversas import criar, usuario

HORA = 3600


@pytest.fixture(autouse=True)
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", tmp_path)
    return tmp_path


def envelhecer(caminho, segundos: int) -> None:
    t = time.time() - segundos
    os.utime(caminho, (t, t))


async def criado_ha(aid: str, horas: int) -> None:
    async with SessionLocal() as s:
        await s.execute(
            update(Attachment).where(Attachment.id == uuid.UUID(aid))
            .values(created_at=Attachment.created_at - timedelta(hours=horas))
        )
        await s.commit()


async def linha(aid: str) -> Attachment | None:
    async with SessionLocal() as s:
        return await s.get(Attachment, uuid.UUID(aid))


async def rodar(dry_run: bool = False) -> dict:
    async with SessionLocal() as s:
        return await varrer(s, dry_run=dry_run)


async def test_arquivo_sem_linha_antigo_some_e_com_linha_fica(client, pasta):
    _, h = await usuario(client)
    anexo = (await subir(client, h, "a.png", PNG, "image/png")).json()
    com_linha = next(pasta.iterdir())
    orfao = pasta / f"{uuid.uuid4()}.png"
    orfao.write_bytes(PNG)
    envelhecer(orfao, 2 * HORA)
    envelhecer(com_linha, 2 * HORA)

    r = await rodar()

    assert not orfao.exists()
    assert com_linha.exists() and await linha(anexo["id"]) is not None
    assert r["files_deleted"] >= 1 and r["bytes_freed"] >= len(PNG)


async def test_arquivo_novo_fica_mesmo_sem_linha(pasta):
    recente = pasta / f"{uuid.uuid4()}.png"
    recente.write_bytes(PNG)
    envelhecer(recente, 30 * 60)

    await rodar()

    assert recente.exists()


async def test_upload_abandonado_ha_mais_de_24h_some_linha_e_arquivo(client, pasta):
    _, h = await usuario(client)
    velho = (await subir(client, h, "velho.png", PNG, "image/png")).json()
    novo = (await subir(client, h, "novo.png", PNG, "image/png")).json()
    for f in pasta.iterdir():
        envelhecer(f, 25 * HORA)
    await criado_ha(velho["id"], 25)
    await criado_ha(novo["id"], 23)

    await rodar()

    assert await linha(velho["id"]) is None
    assert not (pasta / f"{velho['id']}.png").exists()
    assert await linha(novo["id"]) is not None
    assert (pasta / f"{novo['id']}.png").exists()


async def test_dry_run_nao_apaga_nem_grava_evento(client, pasta):
    _, h = await usuario(client)
    velho = (await subir(client, h, "velho.png", PNG, "image/png")).json()
    await criado_ha(velho["id"], 25)
    orfao = pasta / f"{uuid.uuid4()}.png"
    orfao.write_bytes(PNG)
    for f in pasta.iterdir():
        envelhecer(f, 25 * HORA)
    antes = len(await eventos("attachments_swept"))

    r = await rodar(dry_run=True)

    assert orfao.exists() and (pasta / f"{velho['id']}.png").exists()
    assert await linha(velho["id"]) is not None
    assert len(await eventos("attachments_swept")) == antes
    assert str(orfao) in r["files"] and r["rows_deleted"] >= 1


async def test_varredura_grava_evento_com_contagens(pasta):
    orfao = pasta / f"{uuid.uuid4()}.png"
    orfao.write_bytes(PNG)
    envelhecer(orfao, 2 * HORA)
    antes = len(await eventos("attachments_swept"))

    await rodar()

    novos = (await eventos("attachments_swept"))[antes:]
    assert len(novos) == 1
    assert novos[0].payload["files_deleted"] >= 1 and novos[0].payload["bytes_freed"] >= len(PNG)


async def test_symlink_nao_e_seguido(pasta, tmp_path_factory):
    fora = tmp_path_factory.mktemp("fora") / "alvo.png"
    fora.write_bytes(PNG)
    link = pasta / "link.png"
    try:
        link.symlink_to(fora)
    except OSError:
        pytest.skip("sem permissão para criar symlink neste sistema")
    envelhecer(fora, 2 * HORA)

    await rodar()

    assert fora.exists()


async def test_apagar_conversa_com_anexo_libera_o_arquivo(client, pasta):
    async def ok(*_):
        yield "ok"

    app.dependency_overrides[modelo] = lambda: FunctionModel(stream_function=ok, model_name=MODELO)
    try:
        _, h = await usuario(client)
        anexo = (await subir(client, h, "a.png", PNG, "image/png")).json()
        cid = (await criar(client, h))["id"]
        r = await client.post(f"/api/chat/{cid}", json=corpo("oi", [parte(anexo)]), headers=h)
        assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.pop(modelo, None)
    arquivo = pasta / f"{anexo['id']}.png"
    envelhecer(arquivo, 2 * HORA)
    assert (await client.delete(f"/api/conversations/{cid}", headers=h)).status_code == 204

    await rodar()

    assert await linha(anexo["id"]) is None
    assert not arquivo.exists()
