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
    # Teto de tool calls por turno (ticket 06b). Default; a Configuração sobrepõe (ticket 30).
    # 10: um MCP genérico gasta 3 chamadas por ação (search, details, write).
    tool_calls_limit: int = 10
    # Conector Google (ticket 18, ADR 0010). O redirect do OAuth sai de public_base_url.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    public_base_url: str = "http://localhost:8000"
    # Chave Fernet dos tokens dos Conectores. Sem ela, conectar responde 503.
    connectors_key: str | None = None
    # dev libera http:// para o servidor MCP demo (ticket 23). Produção define ENV=prod.
    env: str = "dev"


settings = Settings()

# Janela de contexto (tokens de entrada) por modelo. Fonte: ai.google.dev/gemini-api/docs/models/<modelo>,
# "Input token limit", lida em 23/09/2026. Os três confirmados na doc.
JANELAS_CONTEXTO: dict[str, int] = {
    "gemini-3.8-flash": 1_048_576,
    "gemini-3.7-flash": 1_048_576,
    "gemini-3.1-flash-lite": 1_048_576,
}
