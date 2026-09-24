"""App FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.anexos import router as anexos_router
from app.api_tools import router as api_tools_router
from app.config import settings
from app.auditoria import router as auditoria_router
from app.auth import (
    User,
    UserCreate,
    UserRead,
    auth_backend,
    current_user,
    fastapi_users,
    garantir_admin,
    garantir_conta_demo,
)
from app.chat import router as chat_router
from app.conectores import router as conectores_router
from app.configuracao import cadastro_aberto, cadastro_permitido
from app.configuracao import router as configuracao_router
from app.conversas import router as conversas_router
from app.credito import CapAtingido, PrecoAusente
from app.credito import router as credito_router
from app.db import get_session
from app.estaticos import montar_estaticos
from app.roteador import router as roteador_router
from app.shares import router as shares_router
from app.mcp import router as mcp_router
from app.mcp_oauth import router as mcp_oauth_router
from app.tools import router as tools_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await garantir_conta_demo()
    await garantir_admin()
    yield


# Em prod, sem /docs, /redoc e /openapi.json: o mapa da API não fica público.
_docs = settings.env != "prod"
app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)


# Erro de domínio do Crédito vira HTTP aqui, com o mesmo corpo do HTTPException.
@app.exception_handler(CapAtingido)
async def _cap_atingido(_req: Request, exc: CapAtingido) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=402)


@app.exception_handler(PrecoAusente)
async def _preco_ausente(_req: Request, exc: PrecoAusente) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=500)


app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(cadastro_permitido)],
)
app.include_router(conversas_router)
app.include_router(chat_router)
app.include_router(credito_router)
app.include_router(tools_router)
app.include_router(shares_router)
app.include_router(roteador_router)
app.include_router(auditoria_router)
app.include_router(anexos_router)
app.include_router(configuracao_router)
app.include_router(conectores_router)
app.include_router(mcp_oauth_router)
app.include_router(mcp_router)
app.include_router(api_tools_router)


@app.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Responde ok se o banco responde."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


# Só leitura do próprio Usuário. O router de users do FastAPI-Users expunha PATCH e DELETE /users/{id}.
@app.get("/users/me", response_model=UserRead, tags=["users"])
async def eu(user: Annotated[User, Depends(current_user)]) -> User:
    return user


@app.get("/api/config-publica")
async def config_publica(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, bool | str]:
    """Config que o front lê sem login. Decidida em runtime: a mesma imagem serve dev e prod."""
    return {"env": settings.env, "cadastro_aberto": await cadastro_aberto(session)}


# Manter no fim: catch-all do front depois de todas as rotas da API.
montar_estaticos(app, Path(__file__).resolve().parents[2] / "web" / "dist")
