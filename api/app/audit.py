"""Eventos de auditoria. Tabela somente-inserção (ADR 0007)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[uuid.UUID | None]
    conversation_id: Mapped[uuid.UUID | None]
    event_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cost_micro_usd: Mapped[int | None] = mapped_column(BigInteger)
    latency_ms: Mapped[int | None]
    model: Mapped[str | None] = mapped_column(Text)


async def audit(session: AsyncSession, event_type: str, **fields: Any) -> AuditEvent:
    """Insere um evento na sessão. Quem chama faz o commit."""
    event = AuditEvent(event_type=event_type, **fields)
    session.add(event)
    await session.flush()
    return event
