"""Conector Google: OAuth web flow, tokens cifrados por Usuário, Tools de leitura (ADR 0010) e Rascunho de e-mail (ADR 0013)."""

import asyncio
import base64
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi_users.jwt import decode_jwt, generate_jwt
from pydantic import BaseModel
from pydantic_ai import RunContext
from sqlalchemy import ARRAY, DateTime, ForeignKey, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.config import settings
from app.conversas import Sessao, Usuario
from app.db import Base, SessionLocal

PROVEDOR = "google"
CALLBACK = "/api/connectors/google/callback"
ESCOPO_ENVIO = "https://www.googleapis.com/auth/gmail.send"
ESCOPOS = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    ESCOPO_ENVIO,
]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
DRIVE = "https://www.googleapis.com/drive/v3/files"
AUD_STATE = "tess:google-oauth"
VALIDADE_STATE = 600
# Renova um pouco antes de vencer: o token não expira no meio da chamada.
FOLGA = timedelta(seconds=60)
LIMITE_CHARS = 20_000
TIMEOUT = httpx.Timeout(30.0)
EXPIROU = (
    "A conexão com o Google expirou e não pôde ser renovada. "
    "Peça ao usuário para reconectar a conta Google na tela Conectores."
)
NAO_CONECTADO = "O Google não está conectado. Peça ao usuário para conectar a conta Google na tela Conectores."


class Connector(Base):
    __tablename__ = "connectors"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provedor: Mapped[str] = mapped_column(Text, primary_key=True)
    tokens: Mapped[str] = mapped_column(Text)  # JSON cifrado com Fernet
    escopos: Mapped[list[str]] = mapped_column(ARRAY(Text))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailDraft(Base):
    """Rascunho: e-mail que o modelo preparou e que só sai com clique do dono (ADR 0013)."""

    __tablename__ = "email_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    tool_call_id: Mapped[str | None] = mapped_column(Text)
    para: Mapped[str] = mapped_column(Text)
    assunto: Mapped[str] = mapped_column(Text)
    corpo: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[str | None] = mapped_column(Text)
    in_reply_to: Mapped[str | None] = mapped_column(Text)
    referencias: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text, default="pendente")  # pendente | enviado | descartado
    gmail_message_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConectorExpirado(Exception):
    """Sem token utilizável. A mensagem vai ao modelo como resultado da Tool."""


def transporte_google() -> httpx.AsyncBaseTransport | None:
    """Transporte HTTP das rotas OAuth. None é a rede real. Os testes trocam via dependency_overrides."""
    return None


# ---------- Tokens ----------


def _fernet() -> Fernet:
    if not settings.connectors_key:
        raise HTTPException(status_code=503, detail="CONNECTORS_KEY ausente no servidor")
    return Fernet(settings.connectors_key)


def _cifrar(tokens: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(tokens).encode()).decode()


def _decifrar(valor: str) -> dict[str, Any]:
    return json.loads(_fernet().decrypt(valor.encode()))


def _redirect_uri() -> str:
    return f"{settings.public_base_url}{CALLBACK}"


async def _pedir_token(form: dict[str, str], t: httpx.AsyncBaseTransport | None) -> dict[str, Any]:
    """POST no endpoint de token do Google. Erro HTTP sobe como httpx.HTTPError."""
    base = {"client_id": settings.google_client_id or "", "client_secret": settings.google_client_secret or ""}
    async with httpx.AsyncClient(transport=t, timeout=TIMEOUT) as http:
        r = await http.post(TOKEN_URL, data={**base, **form})
        r.raise_for_status()
        return r.json()


def _expira(resp: dict[str, Any]) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=int(resp.get("expires_in", 3600)))


# REVISAR(human): token válido por mais de FOLGA segue direto. Vencido, renova com o refresh_token
# e grava o novo. O Google às vezes não devolve refresh_token na renovação: mantém o antigo.
# Sem refresh_token ou com invalid_grant (app em Testing expira em 7 dias), vira ConectorExpirado
# com texto claro, que o modelo repassa ao usuário.
async def _token(uid: uuid.UUID, t: httpx.AsyncBaseTransport | None) -> str:
    """Access token do Usuário, renovado se preciso."""
    async with SessionLocal() as s:
        c = await s.get(Connector, (uid, PROVEDOR))
        if c is None:
            raise ConectorExpirado(NAO_CONECTADO)
        tokens = _decifrar(c.tokens)
        if c.expira_em > datetime.now(UTC) + FOLGA:
            return tokens["access_token"]
        if not tokens.get("refresh_token"):
            raise ConectorExpirado(EXPIROU)
        try:
            novo = await _pedir_token({"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]}, t)
        except httpx.HTTPError as e:
            status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
            await audit(s, "connector_refresh_failed", user_id=uid, payload={"provedor": PROVEDOR, "status": status})
            await s.commit()
            raise ConectorExpirado(EXPIROU) from e
        tokens["access_token"] = novo["access_token"]
        tokens["refresh_token"] = novo.get("refresh_token") or tokens["refresh_token"]
        c.tokens = _cifrar(tokens)
        c.expira_em = _expira(novo)
        await audit(s, "connector_refreshed", user_id=uid, payload={"provedor": PROVEDOR})
        await s.commit()
        return tokens["access_token"]


# ---------- Tools ----------


async def _chamar(uid: uuid.UUID, t: httpx.AsyncBaseTransport | None, nome: str, fn) -> str:
    """Abre o cliente HTTP com o token do Usuário e converte qualquer falha em texto para o modelo."""
    try:
        token = await _token(uid, t)
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(transport=t, timeout=TIMEOUT, headers=headers) as http:
            return (await fn(http))[:LIMITE_CHARS]
    except ConectorExpirado as e:
        return str(e)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return EXPIROU
        return f"{nome} falhou: HTTP {e.response.status_code}"
    except httpx.HTTPError as e:
        return f"{nome} falhou: {type(e).__name__}"


def _cabecalhos(payload: dict[str, Any]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in payload.get("headers", [])}


def _decodificar(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _corpo(payload: dict[str, Any]) -> str:
    """Texto do e-mail: prefere text/plain; sem ele, text/html sem as tags."""
    partes: list[dict[str, Any]] = []
    fila = [payload]
    while fila:
        p = fila.pop(0)
        partes.append(p)
        fila.extend(p.get("parts", []))
    for tipo in ("text/plain", "text/html"):
        textos = [_decodificar(p["body"]["data"]) for p in partes if p.get("mimeType") == tipo and p.get("body", {}).get("data")]
        if textos:
            texto = "\n".join(textos)
            return re.sub(r"<[^>]+>", " ", texto) if tipo == "text/html" else texto
    return ""


async def gmail_search(uid: uuid.UUID, query: str, t: httpx.AsyncBaseTransport | None = None) -> str:
    """Busca no Gmail e devolve id, remetente, assunto, data e trecho dos 5 mais recentes."""

    async def buscar(http: httpx.AsyncClient) -> str:
        r = await http.get(f"{GMAIL}/messages", params={"q": query, "maxResults": 5})
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("messages", [])]
        if not ids:
            return "Nenhum e-mail encontrado."
        params = {"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]}
        metas = await asyncio.gather(*(http.get(f"{GMAIL}/messages/{i}", params=params) for i in ids))
        blocos = []
        for n, m in enumerate(metas, 1):
            m.raise_for_status()
            j = m.json()
            h = _cabecalhos(j.get("payload", {}))
            blocos.append(
                f"[{n}] id: {j['id']}\nDe: {h.get('from', '')}\nAssunto: {h.get('subject', '')}\n"
                f"Data: {h.get('date', '')}\n{j.get('snippet', '')}"
            )
        return "\n\n".join(blocos)

    return await _chamar(uid, t, "gmail_search", buscar)


async def gmail_read(uid: uuid.UUID, message_id: str, t: httpx.AsyncBaseTransport | None = None) -> str:
    """Lê um e-mail pelo id: cabeçalhos e corpo em texto."""

    async def ler(http: httpx.AsyncClient) -> str:
        r = await http.get(f"{GMAIL}/messages/{message_id}", params={"format": "full"})
        r.raise_for_status()
        j = r.json()
        payload = j.get("payload", {})
        h = _cabecalhos(payload)
        # Os ids deixam o modelo responder na thread com gmail_send (ADR 0013).
        return (
            f"message_id: {j.get('id', message_id)}\nthread_id: {j.get('threadId', '')}\n"
            f"De: {h.get('from', '')}\nPara: {h.get('to', '')}\nAssunto: {h.get('subject', '')}\n"
            f"Data: {h.get('date', '')}\n\n{_corpo(payload) or '(sem corpo em texto)'}"
        )

    return await _chamar(uid, t, "gmail_read", ler)


# Tipo Google nativo -> formato de exportação em texto.
EXPORTAVEIS = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def _legivel(mime: str) -> bool:
    return mime in EXPORTAVEIS or mime.startswith("text/") or mime == "application/json"


# REVISAR(human): lê só o primeiro arquivo legível (Docs, Sheets, Slides, texto) na ordem do Drive.
# PDF e binários ficam só na lista de "outros achados": ler PDF do Drive fica fora do ticket.
async def drive_search_read(uid: uuid.UUID, query: str, t: httpx.AsyncBaseTransport | None = None) -> str:
    """Busca no Drive por nome ou conteúdo e devolve o texto do arquivo mais relevante."""

    async def buscar_e_ler(http: httpx.AsyncClient) -> str:
        termo = query.replace("\\", "\\\\").replace("'", "\\'")
        q = f"(name contains '{termo}' or fullText contains '{termo}') and trashed = false"
        r = await http.get(DRIVE, params={"q": q, "pageSize": 5, "fields": "files(id,name,mimeType,modifiedTime)"})
        r.raise_for_status()
        arquivos = r.json().get("files", [])
        if not arquivos:
            return "Nenhum arquivo encontrado no Drive."
        alvo = next((a for a in arquivos if _legivel(a["mimeType"])), None)
        outros = "\n".join(f"- {a['name']} ({a['mimeType']}, id {a['id']})" for a in arquivos if a is not alvo)
        if alvo is None:
            return f"Nenhum arquivo em formato de texto. Achados:\n{outros}"
        if alvo["mimeType"] in EXPORTAVEIS:
            c = await http.get(f"{DRIVE}/{alvo['id']}/export", params={"mimeType": EXPORTAVEIS[alvo["mimeType"]]})
        else:
            c = await http.get(f"{DRIVE}/{alvo['id']}", params={"alt": "media"})
        c.raise_for_status()
        texto = f"Arquivo: {alvo['name']} (id {alvo['id']})\n\n{c.text}"
        return f"{texto[: LIMITE_CHARS - 2000]}\n\nOutros achados:\n{outros}" if outros else texto

    return await _chamar(uid, t, "drive_search_read", buscar_e_ler)


AGUARDANDO = (
    "Rascunho criado, aguardando confirmação. O e-mail NÃO foi enviado: o usuário precisa clicar em "
    "Enviar no cartão do rascunho, na tela. Mensagem no chat não envia."
)


async def _resposta_a(uid: uuid.UUID, t: httpx.AsyncBaseTransport | None, thread_id: str) -> tuple[str | None, str]:
    """In-Reply-To e References para responder na thread: o Message-ID da última mensagem dela."""
    token = await _token(uid, t)
    params = {"format": "metadata", "metadataHeaders": ["Message-ID", "References"]}
    async with httpx.AsyncClient(transport=t, timeout=TIMEOUT, headers={"Authorization": f"Bearer {token}"}) as http:
        r = await http.get(f"{GMAIL}/threads/{thread_id}", params=params)
        r.raise_for_status()
    msgs = r.json().get("messages", [])
    h = _cabecalhos(msgs[-1].get("payload", {})) if msgs else {}
    original = h.get("message-id")
    referencias = " ".join(x for x in (h.get("references"), original) if x)
    return original, referencias


# REVISAR(human): a Tool nunca envia. Grava o Rascunho `pendente` e devolve o id ao modelo.
# Com thread_id, busca agora o Message-ID do original: o Rascunho já nasce com In-Reply-To e References,
# e o clique em Enviar não depende de outra leitura. Falha na busca volta como texto e não cria Rascunho.
async def gmail_send(
    uid: uuid.UUID,
    cid: uuid.UUID,
    tool_call_id: str | None,
    para: str,
    assunto: str,
    corpo: str,
    thread_id: str | None = None,
    t: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any] | str:
    """Cria o Rascunho do e-mail. O envio real só acontece no endpoint de confirmação."""
    in_reply_to, referencias = None, None
    if thread_id:
        try:
            in_reply_to, referencias = await _resposta_a(uid, t, thread_id)
        except ConectorExpirado as e:
            return str(e)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            return EXPIROU if status == 401 else f"gmail_send: thread {thread_id} não lida (HTTP {status})"
        except httpx.HTTPError as e:
            return f"gmail_send falhou: {type(e).__name__}"
    d = EmailDraft(
        id=uuid.uuid4(), user_id=uid, conversation_id=cid, tool_call_id=tool_call_id, para=para, assunto=assunto,
        corpo=corpo, thread_id=thread_id, in_reply_to=in_reply_to, referencias=referencias or None,
    )
    async with SessionLocal() as s:
        s.add(d)
        await audit(
            s, "email_draft_created", user_id=uid, conversation_id=cid,
            payload={"draft_id": str(d.id), "para": para, "assunto": assunto, "thread_id": thread_id},
        )
        await s.commit()
    return {
        "draft_id": str(d.id), "estado": "pendente", "para": para, "assunto": assunto, "corpo": corpo,
        "thread_id": thread_id, "aviso": AGUARDANDO,
    }


TOOLS = {"gmail_search", "gmail_read", "drive_search_read", "gmail_send"}


def ligar(nome: str, uid: uuid.UUID, t: httpx.AsyncBaseTransport | None, cid: uuid.UUID | None = None):
    """Função que o modelo vê: só o argumento da tool, com Usuário, Conversa e transporte fixos."""
    if nome == "gmail_send":

        async def rascunhar(
            ctx: RunContext[Any], para: str, assunto: str, corpo: str, thread_id: str | None = None
        ) -> dict[str, Any] | str:
            return await gmail_send(uid, cid, ctx.tool_call_id, para, assunto, corpo, thread_id, t)

        return rascunhar
    if nome == "gmail_read":

        async def ler(message_id: str) -> str:
            return await gmail_read(uid, message_id, t)

        return ler
    fn = gmail_search if nome == "gmail_search" else drive_search_read

    async def buscar(query: str) -> str:
        return await fn(uid, query, t)

    return buscar


# ---------- API ----------


class ConectorOut(BaseModel):
    provedor: str
    conectado: bool
    escopos: list[str] = []
    expira_em: datetime | None = None
    conectado_em: datetime | None = None


router = APIRouter(prefix="/api/connectors", tags=["conectores"])
Transporte = Annotated[httpx.AsyncBaseTransport | None, Depends(transporte_google)]


@router.get("", response_model=list[ConectorOut])
async def listar(session: Sessao, user: Usuario) -> list[ConectorOut]:
    """Estado de cada provedor para o Usuário. Hoje só o Google."""
    c = await session.get(Connector, (user.id, PROVEDOR))
    if c is None:
        return [ConectorOut(provedor=PROVEDOR, conectado=False)]
    return [ConectorOut(provedor=PROVEDOR, conectado=True, escopos=c.escopos, expira_em=c.expira_em, conectado_em=c.created_at)]


# REVISAR(human): o callback chega por GET do browser, sem o Bearer do front. O state é um JWT
# assinado com jwt_secret, com o id do Usuário e validade de 10 min: identifica o dono e barra CSRF.
@router.get("/google/authorize")
async def autorizar(user: Usuario) -> dict[str, str]:
    """URL de consentimento do Google. O front redireciona o browser para ela."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID ausente no servidor")
    _fernet()
    state = generate_jwt({"sub": str(user.id), "aud": AUD_STATE}, settings.jwt_secret, VALIDADE_STATE)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(ESCOPOS),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return {"url": f"{AUTH_URL}?{urlencode(params)}"}


def _voltar(**query: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.public_base_url}/conectores?{urlencode(query)}", status_code=303)


@router.get("/google/callback", include_in_schema=False)
async def callback(
    session: Sessao, t: Transporte, code: str | None = None, state: str | None = None, error: str | None = None
) -> RedirectResponse:
    """Volta do Google: troca o code por tokens, grava cifrado e devolve o browser à tela Conectores."""
    if error:
        return _voltar(erro=error)
    try:
        uid = uuid.UUID(decode_jwt(state or "", settings.jwt_secret, [AUD_STATE])["sub"])
    except Exception:  # noqa: BLE001  state ausente, adulterado ou vencido
        return _voltar(erro="state_invalido")
    if not code:
        return _voltar(erro="sem_code")
    try:
        resp = await _pedir_token(
            {"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect_uri()}, t
        )
    except httpx.HTTPError:
        return _voltar(erro="troca_falhou")
    escopos = resp.get("scope", " ".join(ESCOPOS)).split()
    c = await session.get(Connector, (uid, PROVEDOR))
    antigo = _decifrar(c.tokens).get("refresh_token") if c else None
    tokens = {"access_token": resp["access_token"], "refresh_token": resp.get("refresh_token") or antigo}
    if c is None:
        c = Connector(user_id=uid, provedor=PROVEDOR)
        session.add(c)
    c.tokens, c.escopos, c.expira_em = _cifrar(tokens), escopos, _expira(resp)
    await audit(session, "connector_linked", user_id=uid, payload={"provedor": PROVEDOR, "escopos": escopos})
    await session.commit()
    return _voltar(conectado="1")


@router.delete("/google", status_code=204)
async def revogar(session: Sessao, user: Usuario, t: Transporte) -> Response:
    """Revoga no Google (melhor esforço) e apaga o Conector. As Tools do Google somem das Conversas."""
    c = await session.get(Connector, (user.id, PROVEDOR))
    if c is not None:
        tokens = _decifrar(c.tokens)
        try:
            async with httpx.AsyncClient(transport=t, timeout=TIMEOUT) as http:
                await http.post(REVOKE_URL, data={"token": tokens.get("refresh_token") or tokens["access_token"]})
        except httpx.HTTPError:
            pass  # token já inválido no Google: apagar aqui basta
        await session.delete(c)
        await audit(session, "connector_revoked", user_id=user.id, payload={"provedor": PROVEDOR})
        await session.commit()
    return Response(status_code=204)


# ---------- Rascunho: confirmação por clique (ADR 0013) ----------


class RascunhoOut(BaseModel):
    id: uuid.UUID
    para: str
    assunto: str
    corpo: str
    thread_id: str | None
    em_resposta: bool
    estado: str
    decidido_em: datetime | None


def _saida(d: EmailDraft) -> RascunhoOut:
    return RascunhoOut(
        id=d.id, para=d.para, assunto=d.assunto, corpo=d.corpo, thread_id=d.thread_id,
        em_resposta=d.in_reply_to is not None, estado=d.estado, decidido_em=d.decidido_em,
    )


async def _do_dono(session, user, did: uuid.UUID, travar: bool = False) -> EmailDraft:
    """Rascunho do Usuário. De outro dono é 404: não revela que existe."""
    q = select(EmailDraft).where(EmailDraft.id == did, EmailDraft.user_id == user.id)
    d = await session.scalar(q.with_for_update() if travar else q)
    if d is None:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado")
    return d


def _pendente(d: EmailDraft) -> None:
    if d.estado != "pendente":
        raise HTTPException(status_code=409, detail=f"Rascunho já {d.estado}")


def _mime(d: EmailDraft) -> str:
    """RFC 2822 em base64url, formato do campo `raw` do Gmail."""
    m = EmailMessage()
    m["To"] = d.para
    m["Subject"] = d.assunto
    if d.in_reply_to:
        m["In-Reply-To"] = d.in_reply_to
        m["References"] = d.referencias or d.in_reply_to
    m.set_content(d.corpo)
    return base64.urlsafe_b64encode(m.as_bytes()).decode()


def _texto_erro_gmail(e: httpx.HTTPStatusError) -> str:
    status = e.response.status_code
    if status == 401:
        return EXPIROU
    try:
        motivo = e.response.json()["error"]["message"]
    except Exception:  # noqa: BLE001  corpo fora do formato do Google
        motivo = e.response.text[:300]
    dica = " Reconecte a conta Google em Conectores." if status == 403 else ""
    return f"O Gmail recusou o envio (HTTP {status}): {motivo}.{dica}"


@router.get("/google/drafts/{did}", response_model=RascunhoOut)
async def ler_rascunho(did: uuid.UUID, session: Sessao, user: Usuario) -> RascunhoOut:
    """Estado atual do Rascunho. O cartão do chat lê daqui: a parte gravada na Mensagem fica em `pendente`."""
    return _saida(await _do_dono(session, user, did))


# REVISAR(human): único caminho que envia e-mail. Trava a linha (SELECT ... FOR UPDATE): dois cliques
# simultâneos não enviam duas vezes, o segundo espera e recebe 409. Falha do Gmail mantém `pendente`,
# grava email_send_failed e devolve 502 com o motivo do Google em texto.
@router.post("/google/drafts/{did}/enviar", response_model=RascunhoOut)
async def enviar_rascunho(did: uuid.UUID, session: Sessao, user: Usuario, t: Transporte) -> RascunhoOut:
    """Envia o Rascunho pelo Gmail do dono. Só o clique no front chega aqui."""
    d = await _do_dono(session, user, did, travar=True)
    _pendente(d)
    corpo: dict[str, str] = {"raw": _mime(d)}
    if d.thread_id:
        corpo["threadId"] = d.thread_id
    try:
        token = await _token(user.id, t)
        async with httpx.AsyncClient(transport=t, timeout=TIMEOUT, headers={"Authorization": f"Bearer {token}"}) as http:
            r = await http.post(f"{GMAIL}/messages/send", json=corpo)
            r.raise_for_status()
    except (ConectorExpirado, httpx.HTTPError) as e:
        if isinstance(e, ConectorExpirado):
            texto = str(e)
        elif isinstance(e, httpx.HTTPStatusError):
            texto = _texto_erro_gmail(e)
        else:
            texto = f"Não foi possível falar com o Gmail ({type(e).__name__}). Tente de novo."
        status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
        await audit(
            session, "email_send_failed", user_id=user.id, conversation_id=d.conversation_id,
            payload={"draft_id": str(d.id), "status": status, "erro": texto[:500]},
        )
        await session.commit()
        raise HTTPException(status_code=502, detail=texto) from e
    d.estado, d.gmail_message_id, d.decidido_em = "enviado", r.json().get("id"), datetime.now(UTC)
    await audit(
        session, "email_sent", user_id=user.id, conversation_id=d.conversation_id,
        payload={"draft_id": str(d.id), "message_id": d.gmail_message_id, "thread_id": d.thread_id, "para": d.para},
    )
    await session.commit()
    return _saida(d)


@router.post("/google/drafts/{did}/descartar", response_model=RascunhoOut)
async def descartar_rascunho(did: uuid.UUID, session: Sessao, user: Usuario) -> RascunhoOut:
    """Descarta o Rascunho. Nada vai ao Google."""
    d = await _do_dono(session, user, did, travar=True)
    _pendente(d)
    d.estado, d.decidido_em = "descartado", datetime.now(UTC)
    await audit(
        session, "email_draft_discarded", user_id=user.id, conversation_id=d.conversation_id,
        payload={"draft_id": str(d.id)},
    )
    await session.commit()
    return _saida(d)
