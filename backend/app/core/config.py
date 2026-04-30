from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Hacker Dashboard API"
    debug: bool = False

    # DB — Neon/Supabase postgres (asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hacker"

    # Redis
    redis_url: str = DEFAULT_REDIS_URL

    # LLM
    openai_api_key: str = ""

    # Market data: Kiwoom REST API (domestic/KRX quotes)
    kiwoom_app_key: str = ""
    kiwoom_secret_key: str = ""
    kiwoom_base_url: str = "https://api.kiwoom.com"

    # News: Naver search API
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    # 앱 버전 — 환경변수 APP_VERSION 으로 주입하거나 pyproject.toml 에서 읽는다
    app_version: str = "0.1.0"


settings = Settings()
