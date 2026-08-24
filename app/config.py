from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./app.db"

    openweather_api_key: str | None = None

    cache_ttl_seconds: int = 600
    request_timeout_seconds: float = 10.0
    max_retries: int = 3

    circuit_failure_threshold: int = 5
    circuit_recovery_seconds: float = 30.0


settings = Settings()
