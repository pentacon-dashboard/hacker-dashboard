from pydantic_settings import BaseSettings, SettingsConfigDict


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
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    anthropic_api_key: str = "your-key-here"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # 앱 버전 — 환경변수 APP_VERSION 으로 주입하거나 pyproject.toml 에서 읽는다
    app_version: str = "0.1.0"


settings = Settings()
