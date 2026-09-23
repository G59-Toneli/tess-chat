"""H8: FastAPI-Users com SQLAlchemy async + Postgres (compose, porta 5433). Registro, login JWT, /users/me."""
import uuid
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

SECRET = "spike-secret-nao-usar-em-producao"
engine = create_async_engine("postgresql+asyncpg://spike:spike@127.0.0.1:5433/spike")
Session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass
class User(SQLAlchemyBaseUserTableUUID, Base): pass

class UserRead(schemas.BaseUser[uuid.UUID]): pass
class UserCreate(schemas.BaseUserCreate): pass

async def get_session():
    async with Session() as s:
        yield s
async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET
async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

backend = AuthenticationBackend(name="jwt", transport=BearerTransport(tokenUrl="auth/jwt/login"),
                                get_strategy=lambda: JWTStrategy(secret=SECRET, lifetime_seconds=3600))
fu = FastAPIUsers[User, uuid.UUID](get_user_manager, [backend])

@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(fu.get_auth_router(backend), prefix="/auth/jwt")
app.include_router(fu.get_register_router(UserRead, UserCreate), prefix="/auth")
app.include_router(fu.get_users_router(UserRead, schemas.BaseUserUpdate), prefix="/users")
