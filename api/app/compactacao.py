"""Compactação do histórico por Resumo (ADR 0006). ProcessHistory do Pydantic AI."""

import time
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from functools import cache
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import ProcessHistory
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import RunUsage
from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.config import Settings
from app.credito import acertar
from app.db import Base, SessionLocal

MODELO_RESUMO = "gemini-3.1-flash-lite"
PREFIXO = "Resumo do histórico anterior desta conversa:\n"
INSTRUCAO = (
    "Resuma a conversa abaixo para substituir o histórico dela. Preserve: nomes, fatos que o usuário contou, "
    "preferências, decisões, pedidos em aberto, números, URLs e resultados de tools. "
    "Se houver um resumo anterior, incorpore o conteúdo dele. Escreva em pt-BR, em tópicos curtos, sem comentário."
)
resumidor = Agent(instructions=INSTRUCAO, retries=0)


class Summary(Base):
    """Resumo das Mensagens da Conversa até `ate_message_id`, inclusive. O mais novo vale."""

    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    ate_message_id: Mapped[int] = mapped_column(BigInteger)
    texto: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@cache
def _flash_lite() -> GoogleModel:
    from app.config import settings

    return GoogleModel(MODELO_RESUMO, provider=GoogleProvider(api_key=settings.gemini_paid_api_key))


def modelo_resumo() -> Model:
    """Modelo do Resumo. Os testes trocam via dependency_overrides."""
    return _flash_lite()


# REVISAR(human): compacta quando os tokens de entrada do turno anterior passam do limiar.
# Estritamente maior: no limiar exato ainda cabe. Sem turno anterior, não compacta.
# O input do turno soma todos os requests do turno (tool loop conta mais de uma vez).
def should_compact(usage: RunUsage | None, settings: Settings) -> bool:
    return usage is not None and usage.input_tokens > settings.compactacao_limiar


async def ultimo_resumo(session: AsyncSession, cid: uuid.UUID) -> Summary | None:
    q = select(Summary).where(Summary.conversation_id == cid).order_by(Summary.id.desc()).limit(1)
    return await session.scalar(q)


# REVISAR(human): o corte cai sempre no início de um turno (linha `user`).
# Chamada e retorno de tool ficam dentro da linha `assistant` do mesmo turno,
# então o corte nunca separa o par. Devolve o índice da 1ª linha literal, ou None se não há o que resumir.
def ponto_de_corte(roles: list[str], turnos_literais: int) -> int | None:
    inicios = [i for i, r in enumerate(roles) if r == "user"]
    if len(inicios) <= turnos_literais:
        return None
    corte = inicios[-turnos_literais] if turnos_literais else len(roles)
    return corte or None


def com_resumo(texto: str | None, msgs: list[ModelMessage]) -> list[ModelMessage]:
    """Põe o Resumo no 1º request do histórico. Sem request no começo, vira um request próprio."""
    if texto is None:
        return msgs
    parte = UserPromptPart(PREFIXO + texto)
    if msgs and isinstance(msgs[0], ModelRequest):
        return [replace(msgs[0], parts=[parte, *msgs[0].parts]), *msgs[1:]]
    return [ModelRequest(parts=[parte]), *msgs]


def _como_texto(msgs: list[ModelMessage]) -> str:
    """Histórico em texto corrido para o resumidor. Retorno de tool cortado em 2.000 caracteres."""
    linhas = []
    for m in msgs:
        for p in m.parts:
            if isinstance(p, UserPromptPart):
                linhas.append(f"Usuário: {p.content}")
            elif isinstance(p, TextPart):
                linhas.append(f"Assistente: {p.content}")
            elif isinstance(p, ToolCallPart):
                linhas.append(f"Tool chamada: {p.tool_name}({p.args_as_json_str()})")
            elif isinstance(p, ToolReturnPart):
                linhas.append(f"Resultado de {p.tool_name}: {str(p.content)[:2000]}")
    return "\n".join(linhas)


@dataclass
class Compactacao:
    """Estado de uma compactação num turno. `removidos` corrige o índice das mensagens novas."""

    uid: uuid.UUID
    cid: uuid.UUID
    modelo: Model
    resumo_anterior: str | None
    antigas: list[ModelMessage]
    recentes: list[ModelMessage]
    ate_message_id: int
    tokens_antes: int
    tamanho_historico: int
    removidos: int = 0
    feita: bool = False
    uso: RunUsage | None = None
    custo: int = 0
    latencia: int = 0
    summary_id: int | None = None
    mensagens: tuple[int, int] = (0, 0)

    # REVISAR(human): roda só no passo 1. Depois do passo 1 o Pydantic AI grava a lista processada
    # no histórico do run, então o passo 2 (depois de tool) já vê o Resumo. Falha do resumidor
    # não derruba o turno: grava llm_error e segue com o histórico inteiro.
    async def processar(self, ctx: RunContext[Any], msgs: list[ModelMessage]) -> list[ModelMessage]:
        if self.feita or ctx.run_step != 1:
            return msgs
        self.feita = True
        entrada = _como_texto(self.antigas)
        if self.resumo_anterior:
            entrada = f"Resumo anterior:\n{self.resumo_anterior}\n\nConversa depois dele:\n{entrada}"
        t0 = time.perf_counter()
        try:
            r = await resumidor.run(
                entrada, model=self.modelo, model_settings=GoogleModelSettings(max_tokens=2048)
            )
        except ModelAPIError as exc:
            async with SessionLocal() as s:
                await audit(
                    s,
                    "llm_error",
                    user_id=self.uid,
                    conversation_id=self.cid,
                    model=MODELO_RESUMO,
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    payload={"erro": type(exc).__name__, "etapa": "compaction", "msg": str(exc)[:500]},
                )
                await s.commit()
            return msgs
        novas = com_resumo(r.output, self.recentes + msgs[self.tamanho_historico :])
        self.removidos = len(msgs) - len(novas)
        self.uso = r.usage
        self.latencia = int((time.perf_counter() - t0) * 1000)
        self.mensagens = (len(msgs), len(novas))
        async with SessionLocal() as s:
            resumo = Summary(
                conversation_id=self.cid, ate_message_id=self.ate_message_id, texto=r.output, tokens=self.uso.output_tokens
            )
            s.add(resumo)
            await s.flush()
            self.summary_id = resumo.id
            self.custo = await acertar(s, self.uid, self.cid, None, MODELO_RESUMO, self.uso)
            await s.commit()
        return novas

    async def auditar(self, s: AsyncSession, tokens_depois: int | None) -> None:
        """Evento `compaction` no fim do turno, com o input real do 1º request compactado."""
        if self.uso is None:
            return
        await audit(
            s,
            "compaction",
            user_id=self.uid,
            conversation_id=self.cid,
            model=MODELO_RESUMO,
            input_tokens=self.uso.input_tokens,
            output_tokens=self.uso.output_tokens,
            cost_micro_usd=self.custo,
            latency_ms=self.latencia,
            payload={
                "summary_id": self.summary_id,
                "ate_message_id": self.ate_message_id,
                "tokens_antes": self.tokens_antes,
                "tokens_depois": tokens_depois,
                "mensagens_antes": self.mensagens[0],
                "mensagens_depois": self.mensagens[1],
            },
        )

    def capability(self) -> ProcessHistory[Any]:
        return ProcessHistory(self.processar)
