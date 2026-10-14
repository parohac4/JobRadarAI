import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("jobradar")

INSECURE_SECRETS = {"", "dev-secret-change-me", "change-me-to-long-random-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    demo_mode: bool = False

    admin_email: str = "admin@localhost"
    admin_password: str = "admin"

    database_url: str = "postgresql+asyncpg://jobradar:jobradar_secret@localhost:5432/jobradar"
    sql_echo: bool = False
    root_path: str = ""
    api_docs: bool | None = None

    ai_provider: str = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    auto_evaluate_on_import: bool = False
    ai_daily_max_calls: int = 50

    access_token_expire_minutes: int = 60 * 24
    auth_use_httponly_cookie: bool = True
    auth_cookie_name: str = "jobradar_session"
    enforce_cloudflare: bool = False

    login_max_failures: int = 10
    login_window_seconds: int = 15 * 60

    sync_interval_seconds: int = 900
    worker_enabled: bool = True

    imap_enabled: bool = False
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "JobRadar"

    notify_enabled: bool = False
    notify_min_score: int = 70
    notify_email_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_enabled(self) -> bool:
        return (not self.is_production) if self.api_docs is None else self.api_docs

    @property
    def cookie_secure(self) -> bool:
        return self.is_production

    @property
    def imap_configured(self) -> bool:
        return self.imap_enabled and bool(self.imap_user and self.imap_password)

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        if not self.is_production:
            return self
        if self.secret_key in INSECURE_SECRETS or len(self.secret_key) < 32:
            raise ValueError("APP_ENV=production vyžaduje SECRET_KEY o délce alespoň 32 znaků.")
        if len(self.admin_password) < 12:
            logger.warning("ADMIN_PASSWORD je kratší než 12 znaků – doporučeno změnit.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
