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
    # Tier pago (ADR 0003).
    gemini_paid_api_key: str | None = None
    # Crédito (ADR 0004). Linha em `caps` sobrescreve.
    cap_usuario_micro_usd: int = 2_000_000
    cap_global_micro_usd: int = 20_000_000
    # Teto de saída por request: a reserva usa esse valor inteiro.
    max_output_tokens: int = 8192


settings = Settings()
