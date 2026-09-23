"""Roteador: o Jev escolhe a Tool do turno antes do Gemini, com gate de confiança (ADR 0005)."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.settings import ModelSettings, ToolChoice
from sqlalchemy import select
from typesafe_sdk import AsyncTypeSafeClient, Choice, RetryPolicy

from app.audit import AuditEvent
from app.config import settings
from app.conversas import Sessao, Usuario, conversa_do_usuario

# Nome na Tabela de Preço. O modelo real (ex.: jev-1.13.0) vai só no payload do evento.
PRECO_JEV = "jev-latest"
NENHUMA = "nenhuma"
INSTRUCAO = "Qual ferramenta o assistente deve usar para atender esta mensagem do usuario?"
# Texto das opções validado no spike (hipótese 9). Tool fora daqui usa a descrição do registro.
DESCRICOES = {
    "web_search": "Buscar informacao atual ou factual na internet (noticias, precos, cotacoes, eventos recentes).",
    "web_fetch": "Ler o conteudo de uma URL especifica que o usuario forneceu na mensagem.",
    NENHUMA: "Responder direto, sem ferramenta: conversa, opiniao, explicacao, calculo ou texto criativo.",
}
TIMEOUT_S = 5.0


@dataclass
class Decisao:
    tool: str
    confidence: float
    distribution: dict[str, float]
    modelo: str
    input_tokens: int
    output_tokens: int


@cache
def _cliente() -> AsyncTypeSafeClient:
    # Sem retry: o Roteador é opcional, falha vira AUTO na hora.
    return AsyncTypeSafeClient(
        api_key=settings.typesafe_api_key, retry=RetryPolicy(max_retries=0), timeout=TIMEOUT_S
    )


def cliente_jev() -> AsyncTypeSafeClient | None:
    """Cliente do Jev. None sem chave. Os testes trocam via dependency_overrides."""
    return _cliente() if settings.typesafe_api_key else None


def opcoes(tools: list[tuple[str, str]]) -> dict[str, str]:
    """Critérios da pergunta: Tools ativas (nome, descrição do registro) mais `nenhuma`."""
    return {nome: DESCRICOES.get(nome, desc) for nome, desc in tools} | {NENHUMA: DESCRICOES[NENHUMA]}


async def decidir(client: AsyncTypeSafeClient, texto: str, anexos: list[str], criterios: dict[str, str]) -> Decisao:
    """Pergunta ao Jev qual Tool atende o turno. Erro do SDK sobe como TypeSafeError."""
    r = await client.system_one(
        state={"mensagem_do_usuario": texto, "anexos_na_mensagem": anexos or "nenhum"},
        questions={"tool": Choice(instructions=INSTRUCAO, criteria=criterios)},
    )
    a = r.choices["tool"]
    return Decisao(
        tool=a.choice,
        confidence=a.confidence,
        distribution=dict(a.probabilities),
        modelo=r.model,
        input_tokens=r.usage.input_tokens or 0,
        output_tokens=r.usage.output_tokens or 0,
    )


# REVISAR(human): força a Tool só se o Jev escolheu uma Tool (não `nenhuma`) com confiança >= limiar.
# `nenhuma` com confiança alta também vira AUTO: forçar "sem tool" não ganha nada e quebra se o Jev errar.
# None é AUTO (o Gemini decide). Lista de um nome vira ANY + allowedFunctionNames no Google.
def apply_gate(decision: Decisao | None, threshold: float) -> ToolChoice:
    if decision is None or decision.tool == NENHUMA or decision.confidence < threshold:
        return None
    return [decision.tool]


@dataclass
class Gate(AbstractCapability[Any]):
    """Aplica o tool_choice só no primeiro passo. Depois da Tool, o modelo volta a AUTO e responde."""

    escolha: ToolChoice

    def get_model_settings(self) -> Callable[[RunContext[Any]], ModelSettings]:
        def por_passo(ctx: RunContext[Any]) -> ModelSettings:
            return ModelSettings(tool_choice=self.escolha) if ctx.run_step == 1 and self.escolha else ModelSettings()

        return por_passo


# ---------- API ----------


class DecisaoOut(BaseModel):
    ts: datetime
    tool: str
    confidence: float
    forcada: bool


router = APIRouter(tags=["roteador"])


@router.get("/api/conversations/{cid}/roteador", response_model=list[DecisaoOut])
async def decisoes(cid: uuid.UUID, session: Sessao, user: Usuario) -> list[DecisaoOut]:
    """Decisões do Roteador na Conversa, da mais antiga à mais nova. Lidas do evento router_decision."""
    await conversa_do_usuario(session, user, cid)
    q = (
        select(AuditEvent)
        .where(AuditEvent.conversation_id == cid, AuditEvent.event_type == "router_decision")
        .order_by(AuditEvent.ts, AuditEvent.id)
    )
    return [
        DecisaoOut(ts=e.ts, tool=e.payload["tool"], confidence=e.payload["confidence"], forcada=e.payload["forcada"])
        for e in await session.scalars(q)
    ]
