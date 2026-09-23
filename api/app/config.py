"""Configuração lida do .env na raiz do projeto."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str
    # Só o Alembic usa. A aplicação roda como tess_app.
    database_url_owner: str | None = None
    # Fallback de dev. Produção define JWT_SECRET no .env (ver DECISOES-AUTONOMAS).
    jwt_secret: str = "dev-secret-trocar-em-producao-0123456789"
    demo_password: str = "demo12345"


settings = Settings()
