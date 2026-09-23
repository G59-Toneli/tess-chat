"""Turno em background: registro por Conversa e buffer dos chunks SSE (ADR 0023).

O turno roda numa asyncio.Task fora da request. A resposta HTTP só lê o buffer, então
desconectar o cliente não cancela o run. Buffer em memória: vale para um processo só.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from pydantic_ai import CancellationToken

# Chunk SSE de pé enquanto o turno não acaba. Uma entrada por Conversa: é o que dá o 409.
ATIVOS: dict[uuid.UUID, "TurnoAtivo"] = {}


@dataclass
class TurnoAtivo:
    cid: uuid.UUID
    token: CancellationToken = field(default_factory=CancellationToken)
    task: asyncio.Task[None] | None = None  # referência forte: o loop só guarda referência fraca
    chunks: list[str] = field(default_factory=list)
    fechado: bool = False
    # Parada pedida pelo Usuário (POST /parar). O on_cancel do chat lê para gravar o aviso.
    interrupcao: dict[str, Any] | None = None
    cond: asyncio.Condition = field(default_factory=asyncio.Condition)

    async def escrever(self, chunk: str) -> None:
        async with self.cond:
            self.chunks.append(chunk)
            self.cond.notify_all()

    async def fechar(self) -> None:
        async with self.cond:
            self.fechado = True
            self.cond.notify_all()

    # REVISAR(human): leitor do buffer. Cada leitor tem o próprio índice: replay desde o chunk 0
    # (inclui o `start` com o message id, que o useChat precisa) e depois tail até o turno fechar.
    # Leitor que cai (cliente saiu) só some; o turno e os outros leitores seguem.
    async def ler(self) -> AsyncIterator[str]:
        i = 0
        while True:
            async with self.cond:
                await self.cond.wait_for(lambda: i < len(self.chunks) or self.fechado)
                novos, fim = self.chunks[i:], self.fechado
            i += len(novos)
            for c in novos:
                yield c
            if fim and i == len(self.chunks):
                return

    def parar(self, interrupcao: dict[str, Any]) -> None:
        """Cancela pelo token do Pydantic AI: vira RunCancelled e o on_cancel grava o parcial.
        Task.cancel() viraria CancelledError e o parcial se perderia."""
        self.interrupcao = interrupcao
        self.token.cancel()


def reservar(cid: uuid.UUID) -> TurnoAtivo:
    """Ocupa a vaga da Conversa antes de qualquer await. Turno já ativo: 409."""
    if cid in ATIVOS:
        raise HTTPException(status_code=409, detail="Já há um turno em andamento nesta conversa")
    ATIVOS[cid] = TurnoAtivo(cid)
    return ATIVOS[cid]


async def encerrar(turno: TurnoAtivo) -> None:
    """Tira do registro e acorda os leitores. Nessa ordem: quem lê o fim já pode mandar o próximo POST."""
    if ATIVOS.get(turno.cid) is turno:
        del ATIVOS[turno.cid]
    await turno.fechar()
