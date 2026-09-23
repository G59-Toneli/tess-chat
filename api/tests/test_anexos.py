"""Anexos: upload, posse e entrega ao modelo (ticket 09)."""

import json
import uuid

import httpx2
import pytest
from pydantic_ai.messages import BinaryContent, ModelMessage, ModelRequest, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.chat import MODELO
from app.config import settings
from app.conversas import Attachment
from app.db import SessionLocal
from tests.test_auth import eventos
from tests.test_chat import GRAVADA
from tests.test_conversas import criar, usuario

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n%fim\n"


@pytest.fixture(autouse=True)
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", tmp_path)
    return tmp_path


async def subir(client, h, nome: str, dados: bytes, tipo: str):
    return await client.post("/api/attachments", files={"file": (nome, dados, tipo)}, headers=h)


def corpo(texto: str, arquivos: list[dict]) -> dict:
    partes = [{"type": "text", "text": texto}, *arquivos]
    nova = {"id": uuid.uuid4().hex, "role": "user", "parts": partes}
    return {"trigger": "submit-message", "id": "chat", "messages": [nova]}


def parte(anexo: dict) -> dict:
    return {"type": "file", "url": anexo["url"], "mediaType": anexo["mime_type"], "filename": anexo["filename"]}


def conteudo_do_usuario(msgs: list[ModelMessage]) -> list:
    return [
        c
        for m in msgs
        if isinstance(m, ModelRequest)
        for p in m.parts
        if isinstance(p, UserPromptPart) and not isinstance(p.content, str)
        for c in p.content
    ]


async def test_upload_guarda_arquivo_e_devolve_referencia(client):
    uid, h = await usuario(client)
    r = await subir(client, h, "foto.png", PNG, "image/png")
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["mime_type"] == "image/png"
    assert a["size_bytes"] == len(PNG)
    assert a["url"] == f"/api/attachments/{a['id']}"

    baixado = await client.get(a["url"], headers=h)
    assert baixado.status_code == 200
    assert baixado.content == PNG
    assert (await eventos("attachment_uploaded", user_id=uid))[0].payload["attachment_id"] == a["id"]


async def test_tipo_nao_permitido_415(client, pasta):
    _, h = await usuario(client)
    r = await subir(client, h, "nota.txt", b"texto puro", "text/plain")
    assert r.status_code == 415
    # Tipo declarado mentindo: vale o conteúdo.
    r = await subir(client, h, "falso.png", b"texto puro", "image/png")
    assert r.status_code == 415
    assert list(pasta.iterdir()) == []


async def test_acima_de_20_mb_413(client, pasta):
    _, h = await usuario(client)
    r = await subir(client, h, "grande.pdf", PDF + b"0" * (20 * 1024 * 1024), "application/pdf")
    assert r.status_code == 413
    assert list(pasta.iterdir()) == []


async def test_anexo_de_outro_usuario_404(client, usar_modelo):
    _, h1 = await usuario(client)
    _, h2 = await usuario(client)
    a = (await subir(client, h1, "foto.png", PNG, "image/png")).json()
    assert (await client.get(a["url"], headers=h2)).status_code == 404

    usar_modelo(FunctionModel(stream_function=lambda *_: None, model_name=MODELO))
    cid = (await criar(client, h2))["id"]
    r = await client.post(f"/api/chat/{cid}", json=corpo("o que tem aqui?", [parte(a)]), headers=h2)
    assert r.status_code == 404


async def test_url_externa_no_chat_422(client, usar_modelo):
    _, h = await usuario(client)
    usar_modelo(FunctionModel(stream_function=lambda *_: None, model_name=MODELO))
    cid = (await criar(client, h))["id"]
    externa = {"type": "file", "url": "http://169.254.169.254/x.png", "mediaType": "image/png"}
    r = await client.post(f"/api/chat/{cid}", json=corpo("o que tem aqui?", [externa]), headers=h)
    assert r.status_code == 422


async def test_modelo_recebe_bytes_e_pdf_em_resolucao_media(client, usar_modelo):
    vistas: list[list[ModelMessage]] = []

    async def stream(msgs: list[ModelMessage], _info: AgentInfo):
        vistas.append(msgs)
        yield "ok"

    usar_modelo(FunctionModel(stream_function=stream, model_name=MODELO))
    _, h = await usuario(client)
    img = (await subir(client, h, "foto.png", PNG, "image/png")).json()
    pdf = (await subir(client, h, "doc.pdf", PDF, "application/pdf")).json()
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("resuma", [parte(img), parte(pdf)]), headers=h)
    assert r.status_code == 200, r.text

    itens = conteudo_do_usuario(vistas[0])
    binarios = [c for c in itens if isinstance(c, BinaryContent)]
    assert [(b.media_type, b.data) for b in binarios] == [("image/png", PNG), ("application/pdf", PDF)]
    assert not binarios[0].vendor_metadata
    assert binarios[1].vendor_metadata == {"media_resolution": {"level": "MEDIA_RESOLUTION_MEDIUM"}}


async def test_request_ao_gemini_leva_media_resolution_no_pdf(client, usar_modelo):
    """GoogleModel real, HTTP falso: prova o formato que sai para a API."""
    enviados: list[dict] = []

    def responder(req: httpx2.Request) -> httpx2.Response:
        enviados.append(json.loads(req.content))
        return httpx2.Response(200, content=GRAVADA.read_bytes(), headers={"content-type": "text/event-stream"})

    provider = GoogleProvider(api_key="teste", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(responder)))
    usar_modelo(GoogleModel(MODELO, provider=provider))
    _, h = await usuario(client)
    pdf = (await subir(client, h, "doc.pdf", PDF, "application/pdf")).json()
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("resuma", [parte(pdf)]), headers=h)
    assert r.status_code == 200, r.text

    partes = enviados[0]["contents"][-1]["parts"]
    com_arquivo = [p for p in partes if "inlineData" in p]
    assert com_arquivo[0]["inlineData"]["mime_type"] == "application/pdf"
    assert com_arquivo[0]["mediaResolution"] == {"level": "MEDIA_RESOLUTION_MEDIUM"}



def gemini_gravando(enviados: list[dict]) -> GoogleModel:
    """GoogleModel real com HTTP falso que guarda o JSON de cada request."""

    def responder(req: httpx2.Request) -> httpx2.Response:
        enviados.append(json.loads(req.content))
        return httpx2.Response(200, content=GRAVADA.read_bytes(), headers={"content-type": "text/event-stream"})

    return GoogleModel(MODELO, provider=GoogleProvider(api_key="teste", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(responder))))


def imagens_enviadas(req: dict) -> list[str]:
    return [p["inlineData"]["mime_type"] for c in req["contents"] for p in c["parts"] if "inlineData" in p]


async def test_imagem_volta_ao_modelo_no_turno_seguinte(client, usar_modelo):
    """Bug de produção 23/09: sem a imagem no turno 2, o modelo inventava o texto dela."""
    enviados: list[dict] = []
    usar_modelo(gemini_gravando(enviados))
    _, h = await usuario(client)
    img = (await subir(client, h, "meme.png", PNG, "image/png")).json()
    cid = (await criar(client, h))["id"]

    assert (await client.post(f"/api/chat/{cid}", json=corpo("é verdade?", [parte(img)]), headers=h)).status_code == 200
    assert (await client.post(f"/api/chat/{cid}", json=corpo("o que tá escrito?", []), headers=h)).status_code == 200

    assert imagens_enviadas(enviados[1]) == ["image/png"]


async def test_imagem_sumida_do_disco_vira_aviso(client, usar_modelo, pasta):
    enviados: list[dict] = []
    usar_modelo(gemini_gravando(enviados))
    _, h = await usuario(client)
    img = (await subir(client, h, "meme.png", PNG, "image/png")).json()
    cid = (await criar(client, h))["id"]
    assert (await client.post(f"/api/chat/{cid}", json=corpo("oi", [parte(img)]), headers=h)).status_code == 200
    for f in pasta.iterdir():
        f.unlink()

    assert (await client.post(f"/api/chat/{cid}", json=corpo("e agora?", []), headers=h)).status_code == 200

    assert imagens_enviadas(enviados[1]) == []
    textos = [p.get("text", "") for c in enviados[1]["contents"] for p in c["parts"]]
    assert any("meme.png" in t and "fora do contexto" in t for t in textos)


async def test_pdf_volta_ao_modelo_no_turno_seguinte_em_resolucao_media(client, usar_modelo):
    """Mesmo bug da imagem: sem o PDF no turno 2, o modelo inventava o conteúdo."""
    enviados: list[dict] = []
    usar_modelo(gemini_gravando(enviados))
    _, h = await usuario(client)
    pdf = (await subir(client, h, "contrato.pdf", PDF, "application/pdf")).json()
    cid = (await criar(client, h))["id"]

    assert (await client.post(f"/api/chat/{cid}", json=corpo("resuma", [parte(pdf)]), headers=h)).status_code == 200
    assert (await client.post(f"/api/chat/{cid}", json=corpo("e a cláusula 3?", []), headers=h)).status_code == 200

    arquivos = [p for c in enviados[1]["contents"] for p in c["parts"] if "inlineData" in p]
    assert [p["inlineData"]["mime_type"] for p in arquivos] == ["application/pdf"]
    assert arquivos[0]["mediaResolution"] == {"level": "MEDIA_RESOLUTION_MEDIUM"}


async def test_recarregar_mostra_o_anexo_por_referencia(client, usar_modelo):
    usar_modelo(FunctionModel(stream_function=lambda *_: _ok(), model_name=MODELO))
    _, h = await usuario(client)
    pdf = (await subir(client, h, "contrato.pdf", PDF, "application/pdf")).json()
    cid = (await criar(client, h))["id"]

    r = await client.post(f"/api/chat/{cid}", json=corpo("resuma", [parte(pdf)]), headers=h)
    assert r.status_code == 200, r.text

    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    do_usuario = next(m for m in msgs if m["role"] == "user")
    arquivos = [p for p in do_usuario["parts"] if p["type"] == "file"]
    assert arquivos == [
        {"type": "file", "url": pdf["url"], "mediaType": "application/pdf", "filename": "contrato.pdf"}
    ]
    async with SessionLocal() as s:
        anexo = await s.get(Attachment, uuid.UUID(pdf["id"]))
    assert anexo.message_id == do_usuario["id"]


async def _ok():
    yield "ok"
