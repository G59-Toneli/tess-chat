"""App FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users, garantir_conta_demo
from app.chat import router as chat_router
from app.conversas import router as conversas_router
from app.db import get_session
from app.estaticos import montar_estaticos


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await garantir_conta_demo()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])
app.include_router(conversas_router)
app.include_router(chat_router)


@app.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Responde ok se o banco responde."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


# Manter no fim: catch-all do front depois de todas as rotas da API.
montar_estaticos(app, Path(__file__).resolve().parents[2] / "web" / "dist")
