from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthenticationSettings(BaseSettings):
    web_origin: str = "http://localhost:3000"
    session_cookie_secure: bool = False
    session_ttl_seconds: int = Field(default=604800, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Settings(AuthenticationSettings):
    database_url: str


@lru_cache
def get_authentication_settings() -> AuthenticationSettings:
    return AuthenticationSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
