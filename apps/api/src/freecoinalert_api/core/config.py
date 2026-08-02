from functools import lru_cache
import re
from urllib.parse import urlparse

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
    binance_spot_ws_base_url: str = "wss://stream.binance.com:9443"
    market_event_max_age_seconds: int = Field(default=10, gt=0)
    market_event_future_tolerance_seconds: int = Field(default=2, ge=0)
    market_catalog_refresh_seconds: int = Field(default=21600, gt=0)
    market_state_write_interval_seconds: int = Field(default=1, gt=0)
    market_stream_reconnect_max_seconds: int = Field(default=30, gt=0)
    candle_retention_days: int = Field(default=180, gt=0)
    candle_ws_max_age_seconds: int = Field(default=180, gt=0)
    candle_data_max_lag_seconds: int = Field(default=180, gt=0)
    candle_bootstrap_days: int = Field(default=150, ge=35, le=180)
    candle_reconciliation_lookback_hours: int = Field(default=24, gt=0, le=168)
    candle_recent_reconciliation_seconds: int = Field(default=900, gt=0)
    candle_recent_reconciliation_hours: int = Field(default=6, gt=0, le=168)
    signal_live_catchup_max_days: int = Field(default=7, gt=0, le=7)
    signal_history_days: int = Field(default=90, gt=0, le=180)
    signal_event_retention_days: int = Field(default=365, gt=0)
    signal_sse_max_connections_per_user: int = Field(default=2, gt=0)
    signal_sse_max_connections_per_process: int = Field(default=500, gt=0)
    signal_sse_queue_size: int = Field(default=100, gt=0)
    signal_sse_heartbeat_seconds: int = Field(default=15, gt=0)
    signal_sse_session_revalidation_seconds: int = Field(default=60, gt=0)
    signal_stream_retention_days: int = Field(default=7, gt=0)
    signal_telegram_fanout_batch_size: int = Field(default=100, gt=0, le=1000)
    signal_telegram_fanout_claim_limit: int = Field(default=10, gt=0, le=100)
    signal_telegram_fanout_poll_seconds: float = Field(default=2, gt=0)
    signal_telegram_fanout_max_age_seconds: int = Field(default=900, gt=0)

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

    @field_validator("binance_spot_ws_base_url")
    @classmethod
    def validate_binance_spot_ws_base_url(cls, value: str) -> str:
        parsed = urlparse(value)

        if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
            raise ValueError("BINANCE_SPOT_WS_BASE_URL must be a WebSocket URL.")

        if parsed.hostname == "stream.binance.com" and parsed.scheme != "wss":
            raise ValueError("BINANCE_SPOT_WS_BASE_URL must use wss for Binance production.")

        return value.rstrip("/")


class Settings(AuthenticationSettings):
    database_url: str


@lru_cache
def get_authentication_settings() -> AuthenticationSettings:
    return AuthenticationSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
