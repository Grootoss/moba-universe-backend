"""Application settings from environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Single source: project root `.env` (also works when cwd is backend/)
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://moba:moba@127.0.0.1:5432/mobauniverse"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 14
    cors_origins: str = "http://localhost:5173,https://mobauniverse.com"
    site_url: str = "https://mobauniverse.com"
    # Only used by scripts/seed.py when creating the first admin
    admin_password: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
