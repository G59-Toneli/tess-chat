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
    # Busca da tool web_search (ticket 10). Sem chave, a tool responde indisponível.
    tavily_api_key: str | None = None
    # Roteador Jev (ADR 0005). Sem chave, o Roteador cai em AUTO.
    typesafe_api_key: str | None = None
    # Default do limiar do gate. A Configuração sobrepõe (ticket 14).
    roteador_limiar: float = 0.7
    # Crédito (ADR 0004). Linha em `caps` sobrescreve.
    cap_usuario_micro_usd: int = 2_000_000
    cap_global_micro_usd: int = 20_000_000
    # Teto de saída por request: a reserva usa esse valor inteiro.
    max_output_tokens: int = 8192
    # Compactação (ADR 0006). O limiar é default; a Configuração sobrepõe (ticket 14).
    compactacao_limiar: int = 100_000
    compactacao_turnos_literais: int = 2
    # Anexos (ticket 09). Fora do git (`data/` no .gitignore).
    attachments_dir: Path = Path(__file__).resolve().parents[2] / "data" / "attachments"
    # Teto de tool calls por turno (ticket 06b). Vai para a Configuração no ticket 14.
    tool_calls_limit: int = 5


settings = Settings()
