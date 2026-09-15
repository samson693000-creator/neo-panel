from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
DEFAULT_SQLITE = f"sqlite+aiosqlite:///{(DATA_DIR / 'bot.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"), extra="ignore"
    )

    app_name: str = "AI Bot Control Panel"
    debug: bool = False

    database_url: str = DEFAULT_SQLITE
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change_me"
    encryption_key: str = ""
    access_token_expire_minutes: int = 720

    admin_username: str = "admin"
    admin_password: str = "admin12345"

    cors_origins: str = (
        "http://127.0.0.1:8000,http://localhost:8000,"
        "http://localhost:5173,http://localhost:8080"
    )
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
