"""Auth com FastAPI-Users: cadastro, login JWT, tabela users, conta demo."""

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, exceptions, schemas
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.config import settings
from app.db import Base, SessionLocal, get_session

DEMO_EMAIL = "demo@toneli.dev.br"


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[SQLAlchemyUserDatabase]:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.jwt_secret
    verification_token_secret = settings.jwt_secret

    @property
    def _session(self) -> AsyncSession:
        return self.user_db.session

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        await audit(self._session, "user_registered", user_id=user.id, payload={"email": user.email})
        await self._session.commit()

    async def on_after_login(
        self, user: User, request: Request | None = None, response: Response | None = None
    ) -> None:
        await audit(self._session, "login_ok", user_id=user.id, payload={"email": user.email})
        await self._session.commit()

    # REVISAR(human): FastAPI-Users não tem hook de falha de login. Sobrescrevo
    # authenticate: se o pai devolve None (e-mail inexistente, senha errada ou
    # conta inativa), grava login_failed só com o e-mail, nunca a senha.
    async def authenticate(self, credentials: OAuth2PasswordRequestForm) -> User | None:
        user = await super().authenticate(credentials)
        if user is None or not user.is_active:
            await audit(
                self._session,
                "login_failed",
                user_id=user.id if user else None,
                payload={"email": credentials.username},
            )
            await self._session.commit()
        return user


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.jwt_secret, lifetime_seconds=60 * 60 * 24)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=BearerTransport(tokenUrl="auth/jwt/login"),
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_user = fastapi_users.current_user(active=True)


# REVISAR(human): seed da conta demo no startup, idempotente. Se já existe,
# não mexe (não reseta senha). Alternativa descartada: migração de dados.
async def garantir_conta_demo() -> None:
    """Cria a conta demo se ela não existe."""
    async with SessionLocal() as session:
        manager = UserManager(SQLAlchemyUserDatabase(session, User))
        try:
            await manager.create(UserCreate(email=DEMO_EMAIL, password=settings.demo_password))
        except exceptions.UserAlreadyExists:
            pass
