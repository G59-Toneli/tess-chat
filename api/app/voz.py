"""Ligação: Ticket de Ligação, proxy WebSocket browser ⇄ Gemini Live, crédito e auditoria (ADR 0026, 0027).

Contrato com o browser em docs/PROTOCOLO-LIGACAO.md. Nomes do SDK em spike/live/RESULTADO.md.
Registro em memória, como o turno do ADR 0023: vale para um processo só.
"""

import asyncio
import base64
import binascii
import json
import logging
import secrets
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, suppress
from dataclasses import asdict, dataclass, field
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import turnos
from app.audit import audit
from app.auth import User, current_user
from app.config import settings
from app.conversas import conversa_do_usuario
from app.credito import MILHAO, CapAtingido, CreditLedger, PrecoAusente, PrecoModelo, caber, preco_vigente
from app.db import SessionLocal, get_session

log = logging.getLogger(__name__)

# Adendo de voz da sessão 2 do spike 75. O texto do ADR 0026 item 8 ("sem tela, diga que não vê nada")
# fez o modelo negar a tela que tinha. Primeiro diz que as imagens chegam.
ADENDO_VOZ = (
    "Você é um assistente de voz. Responda em português brasileiro, curto e falado, sem markdown. "
    "Quando o usuário compartilha a tela, você recebe imagens dela e pode descrevê-las. "
    "Se não chegou nenhuma imagem, diga que não vê nada."
)
AUDIO_IN = "audio/pcm;rate=16000"
# Áudio de saída do Gemini: PCM16 24 kHz mono = 48000 bytes por segundo.
BYTES_AUDIO_OUT_S = 48_000
# Medidos no spike 75: ~25 tokens por segundo de áudio, 264 tokens por Frame.
TOKENS_AUDIO_S = 25
TOKENS_FRAME = 264


class SessaoLive(Protocol):
    """O que o relay usa da sessão Live. O SDK real e o Gemini falso dos testes cumprem."""

    async def send_realtime_input(self, *, audio: types.Blob | None = None, video: types.Blob | None = None) -> None: ...

    def receive(self) -> AsyncIterator[types.LiveServerMessage]: ...


Conector = Callable[[str], AbstractAsyncContextManager[SessaoLive]]


def _conectar(instrucao: str) -> AbstractAsyncContextManager[SessaoLive]:
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=settings.gemini_live_voz)
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        # Sem compressão, sessão com vídeo morre em 2 min (ADR 0026 item 5).
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
        system_instruction=instrucao,
    )
    cliente = genai.Client(api_key=settings.gemini_live_api_key)
    return cliente.aio.live.connect(model=settings.gemini_live_modelo, config=config)


def conectar_gemini() -> Conector:
    """Seam do Gemini Live. Os testes trocam via dependency_overrides."""
    return _conectar


@dataclass
class UsoLigacao:
    """Tokens por modalidade, somados de todos os turnos."""

    texto_in: int = 0
    audio_in: int = 0
    imagem_in: int = 0
    texto_out: int = 0
    audio_out: int = 0
    pensamento: int = 0

    def somar(self, um: types.UsageMetadata) -> None:
        for d in um.prompt_tokens_details or []:
            self._somar(d, "in")
        for d in um.response_tokens_details or []:
            self._somar(d, "out")
        self.pensamento += um.thoughts_token_count or 0

    def _somar(self, d: types.ModalityTokenCount, lado: str) -> None:
        # Frame vai como `video=`; o spike viu IMAGE, VIDEO entra no mesmo preço por garantia.
        nome = {
            types.MediaModality.TEXT: "texto",
            types.MediaModality.AUDIO: "audio",
            types.MediaModality.IMAGE: "imagem",
            types.MediaModality.VIDEO: "imagem",
        }
        if (m := nome.get(d.modality)) and hasattr(self, f"{m}_{lado}"):
            setattr(self, f"{m}_{lado}", getattr(self, f"{m}_{lado}") + (d.token_count or 0))

    @property
    def entrada(self) -> int:
        return self.texto_in + self.audio_in + self.imagem_in

    @property
    def saida(self) -> int:
        """Convenção do Ledger: output já inclui o pensamento."""
        return self.texto_out + self.audio_out + self.pensamento


def _preco(v: int | None, preco: PrecoModelo) -> int:
    if v is None:
        raise PrecoAusente(f"Modelo sem preço de áudio ou imagem na Tabela de Preço: {preco.model}")
    return v


def debit_ligacao(uso: UsoLigacao, preco: PrecoModelo) -> int:
    """Custo em micro-USD, cada modalidade no seu preço. Pensamento ao preço de thinking. Arredonda para cima."""
    total = (
        uso.texto_in * preco.input_micro_usd_1m
        + uso.audio_in * _preco(preco.audio_input_micro_usd_1m, preco)
        + uso.imagem_in * _preco(preco.image_input_micro_usd_1m, preco)
        + uso.texto_out * preco.output_micro_usd_1m
        + uso.audio_out * _preco(preco.audio_output_micro_usd_1m, preco)
        + uso.pensamento * preco.thinking_micro_usd_1m
    )
    return -(-total // MILHAO)


def uso_maximo() -> UsoLigacao:
    """Estimativa da Ligação inteira no limite: fala dos dois lados o tempo todo e um Frame por segundo."""
    s = settings.ligacao_limite_s
    return UsoLigacao(audio_in=TOKENS_AUDIO_S * s, audio_out=TOKENS_AUDIO_S * s, imagem_in=TOKENS_FRAME * s * settings.ligacao_fps)


async def _reservar(session: AsyncSession, user_id: uuid.UUID, cid: uuid.UUID) -> None:
    """Reserva de 9 min (ADR 0027): recusa com CapAtingido. Não grava nada no Ledger."""
    preco = await preco_vigente(session, settings.gemini_live_modelo)
    await caber(session, user_id, cid, settings.gemini_live_modelo, debit_ligacao(uso_maximo(), preco))


@dataclass
class Ticket:
    user_id: uuid.UUID
    cid: uuid.UUID
    expira: float


@dataclass
class Ligacao:
    user_id: uuid.UUID
    cid: uuid.UUID
    turno: turnos.TurnoAtivo
    inicio: float = field(default_factory=time.monotonic)
    uso: UsoLigacao = field(default_factory=UsoLigacao)
    turnos_com_uso: int = 0
    bytes_agente: int = 0
    frames: int = 0
    ultimo_frame: float = 0.0
    tela: bool = False
    # Falas em memória. O ticket 77 grava como Mensagens no fim único.
    falas: list[dict[str, str]] = field(default_factory=list)
    fala_agente: str = ""
    encerrada: bool = False


TICKETS: dict[str, Ticket] = {}
# Uma Ligação por Usuário. len() é o teto global.
LIGACOES: dict[uuid.UUID, Ligacao] = {}


def _vaga(user_id: uuid.UUID, cid: uuid.UUID) -> tuple[int, str] | None:
    """Status e mensagem da recusa, ou None se cabe mais uma Ligação."""
    if user_id in LIGACOES:
        return 409, "Você já está numa Ligação"
    if cid in turnos.ATIVOS:
        return 409, "Já há um turno em andamento nesta conversa"
    if len(LIGACOES) >= settings.ligacao_teto_global:
        return 429, "Muitas Ligações ao mesmo tempo. Tente de novo em instantes."
    return None


router = APIRouter(prefix="/api/voz", tags=["voz"])


class PedidoTicket(BaseModel):
    conversa_id: uuid.UUID


class TicketOut(BaseModel):
    ticket: str
    expira_em: int


@router.post("/ticket")
async def criar_ticket(
    body: PedidoTicket,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
) -> TicketOut:
    """Ticket de Ligação: uso único, curto. Recusa antes o que o WebSocket recusaria (402, 404, 409, 429)."""
    await conversa_do_usuario(session, user, body.conversa_id)
    if recusa := _vaga(user.id, body.conversa_id):
        raise HTTPException(*recusa)
    await _reservar(session, user.id, body.conversa_id)
    agora = time.monotonic()
    for velho in [k for k, t in TICKETS.items() if t.expira <= agora]:
        del TICKETS[velho]
    codigo = secrets.token_urlsafe(32)
    TICKETS[codigo] = Ticket(user.id, body.conversa_id, agora + settings.ligacao_ticket_s)
    return TicketOut(ticket=codigo, expira_em=settings.ligacao_ticket_s)


# REVISAR(human): valida o ticket da URL. `pop` antes de checar a validade: o código some no
# primeiro uso, mesmo expirado, então não existe segunda tentativa com o mesmo código. Vale 30 s
# porque só cobre o intervalo entre o POST e o upgrade do WebSocket. O JWT não vai na URL:
# a URL fica no log do nginx, e o JWT vale 24 h; o ticket vazado no log já está gasto.
def _consumir(codigo: str) -> Ticket | None:
    t = TICKETS.pop(codigo, None)
    if t is None or t.expira <= time.monotonic():
        return None
    return t


@router.websocket("/ws")
async def ligacao(websocket: WebSocket, conectar: Annotated[Conector, Depends(conectar_gemini)], ticket: str = "") -> None:
    """Uma Ligação. Recusa depois do upgrade, com close code do protocolo: close antes do accept vira 403."""
    await websocket.accept()
    t = _consumir(ticket)
    if t is None:
        return await websocket.close(4401)
    # Sem await entre a checagem e o registro: dois WebSockets não passam juntos.
    if recusa := _vaga(t.user_id, t.cid):
        return await websocket.close(4000 + recusa[0])
    lig = Ligacao(t.user_id, t.cid, turnos.reservar(t.cid))
    LIGACOES[t.user_id] = lig
    async with AsyncExitStack() as pilha:
        try:
            async with SessionLocal() as s:
                await _reservar(s, t.user_id, t.cid)
            sessao = await pilha.enter_async_context(conectar(ADENDO_VOZ))
        except CapAtingido:
            await _liberar(lig)
            return await websocket.close(4402)
        except Exception:
            log.exception("Ligação %s não abriu", t.cid)
            await _liberar(lig)
            return await websocket.close(4500)
        motivo = "erro"
        try:
            async with SessionLocal() as s:
                await audit(
                    s,
                    "voice_call_started",
                    user_id=t.user_id,
                    conversation_id=t.cid,
                    model=settings.gemini_live_modelo,
                    payload={"limite_s": settings.ligacao_limite_s, "voz": settings.gemini_live_voz},
                )
                await s.commit()
            await websocket.send_json({"tipo": "pronto", "limite_s": settings.ligacao_limite_s})
            motivo = await _relay(websocket, sessao, lig)
        finally:
            await _encerrar(websocket, lig, motivo)


# REVISAR(human): o relay. Duas tasks, uma por sentido, porque cada lado manda quando quer:
# o microfone não espera a resposta, e o Gemini fala sem o browser pedir. `asyncio.wait` com
# FIRST_COMPLETED acorda quando uma acaba; o timeout é o limite de 9 min. A outra é cancelada
# na hora e esperada (`gather`), para nenhuma task ficar escrevendo num WebSocket morto.
# Motivo: a task devolve `desligou` ou `queda`; exceção (o Gemini caiu) é `erro`; timeout é `limite`.
async def _relay(websocket: WebSocket, sessao: SessaoLive, lig: Ligacao) -> str:
    subir = asyncio.create_task(_browser_para_gemini(websocket, sessao, lig))
    descer = asyncio.create_task(_gemini_para_browser(websocket, sessao, lig))
    try:
        feitas, _ = await asyncio.wait(
            {subir, descer}, timeout=settings.ligacao_limite_s, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        subir.cancel()
        descer.cancel()
        await asyncio.gather(subir, descer, return_exceptions=True)
    if not feitas:
        return "limite"
    task = subir if subir in feitas else descer
    if (exc := task.exception()) is not None:
        log.warning("Ligação %s caiu: %r", lig.cid, exc)
        return "erro"
    return task.result()


async def _browser_para_gemini(websocket: WebSocket, sessao: SessaoLive, lig: Ligacao) -> str:
    while True:
        msg = await websocket.receive()
        if msg["type"] == "websocket.disconnect":
            return "queda"
        if (pcm := msg.get("bytes")) is not None:
            await sessao.send_realtime_input(audio=types.Blob(data=pcm, mime_type=AUDIO_IN))
            continue
        try:
            dado = json.loads(msg.get("text") or "")
        except ValueError:
            continue
        match dado.get("tipo") if isinstance(dado, dict) else None:
            case "desligar":
                return "desligou"
            case "tela":
                await _tela(lig, bool(dado.get("ativa")))
            case "frame":
                if (jpeg := _frame(lig, dado.get("jpeg"))) is not None:
                    await sessao.send_realtime_input(video=types.Blob(data=jpeg, mime_type="image/jpeg"))


def _frame(lig: Ligacao, b64: Any) -> bytes | None:
    """Frame acima do fps da config é descartado (folga de 20% para o timer do browser)."""
    agora = time.monotonic()
    if not isinstance(b64, str) or agora - lig.ultimo_frame < 0.8 / settings.ligacao_fps:
        return None
    try:
        jpeg = base64.b64decode(b64, validate=True)
    except binascii.Error:
        return None
    lig.ultimo_frame, lig.frames = agora, lig.frames + 1
    return jpeg


async def _tela(lig: Ligacao, ativa: bool) -> None:
    """Evento só na mudança de estado, não por Frame."""
    if ativa == lig.tela:
        return
    lig.tela = ativa
    async with SessionLocal() as s:
        await audit(
            s,
            "screen_share_started" if ativa else "screen_share_stopped",
            user_id=lig.user_id,
            conversation_id=lig.cid,
        )
        await s.commit()


async def _gemini_para_browser(websocket: WebSocket, sessao: SessaoLive, lig: Ligacao) -> str:
    """`receive()` do SDK acaba a cada turn_complete: o laço de fora pede o turno seguinte.
    Rodada sem mensagem nenhuma é o Gemini fechado."""
    while True:
        vazio = True
        async for m in sessao.receive():
            vazio = False
            for saida in _traduzir(lig, m):
                try:
                    if isinstance(saida, bytes):
                        await websocket.send_bytes(saida)
                    else:
                        await websocket.send_json(saida)
                except Exception:
                    return "queda"
        if vazio:
            raise ConnectionError("Gemini Live fechou a sessão")


def _traduzir(lig: Ligacao, m: types.LiveServerMessage) -> list[bytes | dict[str, Any]]:
    """Mensagem do Gemini → mensagens do protocolo. Guarda uso e falas na Ligação.
    Transcrição do agente vai acumulada (texto inteiro até agora); `final` fecha a fala no turn_complete."""
    saidas: list[bytes | dict[str, Any]] = []
    if m.usage_metadata:
        lig.uso.somar(m.usage_metadata)
        lig.turnos_com_uso += 1
    sc = m.server_content
    if sc is None:
        return saidas
    if sc.input_transcription and sc.input_transcription.text:
        texto = sc.input_transcription.text.strip()
        lig.falas.append({"origem": "usuario", "texto": texto})
        saidas.append({"tipo": "transcricao", "origem": "usuario", "texto": texto, "final": True})
    for p in (sc.model_turn.parts or []) if sc.model_turn else []:
        if p.inline_data and p.inline_data.data:
            lig.bytes_agente += len(p.inline_data.data)
            saidas.append(p.inline_data.data)
    if sc.output_transcription and sc.output_transcription.text:
        lig.fala_agente += sc.output_transcription.text
        saidas.append({"tipo": "transcricao", "origem": "agente", "texto": lig.fala_agente, "final": False})
    if sc.interrupted:
        saidas.append({"tipo": "interrompido"})
    if sc.turn_complete and lig.fala_agente:
        texto, lig.fala_agente = lig.fala_agente.strip(), ""
        lig.falas.append({"origem": "agente", "texto": texto})
        saidas.append({"tipo": "transcricao", "origem": "agente", "texto": texto, "final": True})
    return saidas


# REVISAR(human): acerto de crédito da Ligação. Soma o usage_metadata de todos os turnos: cada
# turno cobra o contexto inteiro de novo (spike 75). Preço de tabela mesmo na chave free (ADR 0027):
# o Cap mede "quanto custaria". Sem nenhum usage_metadata (a Ligação caiu antes do 1º turn_complete),
# estima pela duração: 25 tokens/s de entrada o tempo todo, 25 tokens/s de saída no tempo de fala
# do agente (bytes de áudio recebidos), 264 tokens se chegou Frame. Uma linha no Ledger.
async def _acertar(session: AsyncSession, lig: Ligacao, duracao_s: float) -> tuple[UsoLigacao, int, bool]:
    estimado = lig.turnos_com_uso == 0
    uso = lig.uso
    if estimado:
        uso = UsoLigacao(
            audio_in=round(TOKENS_AUDIO_S * duracao_s),
            audio_out=round(TOKENS_AUDIO_S * lig.bytes_agente / BYTES_AUDIO_OUT_S),
            imagem_in=TOKENS_FRAME if lig.frames else 0,
        )
    preco = await preco_vigente(session, settings.gemini_live_modelo)
    custo = debit_ligacao(uso, preco)
    session.add(
        CreditLedger(
            user_id=lig.user_id,
            conversation_id=lig.cid,
            message_id=None,
            model=preco.model,
            price_id=preco.id,
            input_tokens=uso.entrada,
            output_tokens=uso.saida,
            thinking_tokens=uso.pensamento,
            cache_read_tokens=0,
            cost_micro_usd=custo,
        )
    )
    return uso, custo, estimado


# REVISAR(human): fim único. Desligar, limite, queda do browser e queda do Gemini passam aqui,
# chamado do `finally`. Ordem: acerto e voice_call_ended com commit, depois libera a vaga, depois
# manda `fim`. Quem recebe o `fim` já pode mandar texto. `encerrada` segura a segunda chamada.
# A vaga sai mesmo se o acerto falhar: sem isso, 409 eterno na Conversa.
async def _encerrar(websocket: WebSocket, lig: Ligacao, motivo: str) -> None:
    if lig.encerrada:
        return
    lig.encerrada = True
    duracao = time.monotonic() - lig.inicio
    try:
        async with SessionLocal() as s:
            if lig.tela:
                await audit(s, "screen_share_stopped", user_id=lig.user_id, conversation_id=lig.cid)
            uso, custo, estimado = await _acertar(s, lig, duracao)
            await audit(
                s,
                "voice_call_ended",
                user_id=lig.user_id,
                conversation_id=lig.cid,
                model=settings.gemini_live_modelo,
                input_tokens=uso.entrada,
                output_tokens=uso.saida,
                cost_micro_usd=custo,
                latency_ms=round(duracao * 1000),
                payload={
                    "motivo": motivo,
                    "duracao_s": round(duracao, 1),
                    "tokens": asdict(uso),
                    "estimado": estimado,
                    "turnos": lig.turnos_com_uso,
                    "frames": lig.frames,
                },
            )
            await s.commit()
    except Exception:
        log.exception("acerto da Ligação %s falhou", lig.cid)
    finally:
        await _liberar(lig)
        if motivo != "queda":
            with suppress(Exception):
                if motivo == "erro":
                    await websocket.send_json({"tipo": "erro", "mensagem": "A ligação caiu. Tente de novo."})
                await websocket.send_json({"tipo": "fim", "motivo": motivo})
                await websocket.close(1000)


async def _liberar(lig: Ligacao) -> None:
    if LIGACOES.get(lig.user_id) is lig:
        del LIGACOES[lig.user_id]
    await turnos.encerrar(lig.turno)
