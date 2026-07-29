from functools import lru_cache
import re

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthenticationSettings(BaseSettings):
    web_origin: str = "http://localhost:3000"
    session_cookie_secure: bool = False
    session_ttl_seconds: int = Field(default=604800, gt=0)
    telegram_bot_username: str | None = None
    telegram_bot_token: str | None = None
    telegram_link_ttl_seconds: int = Field(default=600, gt=0)
    telegram_update_retention_days: int = Field(default=30, gt=0)
    binance_spot_base_url: str = "https://api.binance.com"
    market_catalog_max_age_seconds: int = Field(default=86400, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("telegram_bot_username")
    @classmethod
    def validate_telegram_bot_username(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None

        if re.fullmatch(r"[A-Za-z0-9_]+", value) is None:
            raise ValueError("TELEGRAM_BOT_USERNAME must use Telegram username characters.")

        return value


class Settings(AuthenticationSettings):
    database_url: str


@lru_cache
def get_authentication_settings() -> AuthenticationSettings:
    return AuthenticationSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
