from datetime import UTC, datetime
from functools import lru_cache
import re
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PRODUCTION_TELEGRAM_BOT_API_BASE_URL = "https://api.telegram.org/bot"
PRODUCTION_TELEGRAM_BOT_FILE_BASE_URL = "https://api.telegram.org/file/bot"
PRODUCTION_TELEGRAM_PUBLIC_BOT_BASE_URL = "https://t.me"
E2E_TELEGRAM_BOT_API_BASE_URL = "http://provider-simulator:9000/bot"
E2E_TELEGRAM_BOT_FILE_BASE_URL = "http://provider-simulator:9000/file/bot"
E2E_TELEGRAM_PUBLIC_BOT_BASE_URL = "http://provider-simulator:9000/telegram"
E2E_BINANCE_SPOT_BASE_URL = "http://provider-simulator:9000"
E2E_BINANCE_SPOT_WS_BASE_URL = "ws://provider-simulator:9000"


class AuthenticationSettings(BaseSettings):
    web_origin: str = "http://localhost:3000"
    session_cookie_secure: bool = False
    session_ttl_seconds: int = Field(default=604800, gt=0)
    telegram_bot_username: str | None = None
    telegram_bot_token: str | None = None
    telegram_link_ttl_seconds: int = Field(default=600, gt=0)
    telegram_update_retention_days: int = Field(default=30, gt=0)
    telegram_bot_api_base_url: str = PRODUCTION_TELEGRAM_BOT_API_BASE_URL
    telegram_bot_file_base_url: str = PRODUCTION_TELEGRAM_BOT_FILE_BASE_URL
    telegram_public_bot_base_url: str = PRODUCTION_TELEGRAM_PUBLIC_BOT_BASE_URL
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
    historical_analysis_worker_poll_seconds: float = Field(default=2, gt=0)
    historical_analysis_worker_claim_limit: int = Field(default=1, ge=1, le=4)
    historical_analysis_worker_stale_seconds: int = Field(default=600, ge=60)
    historical_analysis_retention_days: int = Field(default=30, ge=1)
    historical_analysis_cleanup_batch_size: int = Field(default=100, ge=1, le=1000)
    e2e_test_mode: bool = False
    e2e_clock_now: datetime | None = None
    e2e_control_token: str | None = None
    e2e_worker_gate_enabled: bool = False

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

    @field_validator("e2e_clock_now")
    @classmethod
    def validate_e2e_clock_now(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("E2E_CLOCK_NOW must be an aware UTC timestamp.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_provider_configuration(self) -> "AuthenticationSettings":
        if not self.e2e_test_mode:
            if (
                self.telegram_bot_api_base_url != PRODUCTION_TELEGRAM_BOT_API_BASE_URL
                or self.telegram_bot_file_base_url != PRODUCTION_TELEGRAM_BOT_FILE_BASE_URL
                or self.telegram_public_bot_base_url != PRODUCTION_TELEGRAM_PUBLIC_BOT_BASE_URL
            ):
                raise ValueError(
                    "Custom Telegram provider URLs require E2E_TEST_MODE=true."
                )
            if self.e2e_clock_now is not None:
                raise ValueError("E2E_CLOCK_NOW requires E2E_TEST_MODE=true.")
            if self.e2e_worker_gate_enabled:
                raise ValueError("E2E_WORKER_GATE_ENABLED requires E2E_TEST_MODE=true.")
            return self

        if self.e2e_clock_now is None:
            raise ValueError("E2E_CLOCK_NOW is required when E2E_TEST_MODE=true.")
        if not self.e2e_control_token:
            raise ValueError("E2E_CONTROL_TOKEN is required when E2E_TEST_MODE=true.")
        if self.telegram_bot_api_base_url != E2E_TELEGRAM_BOT_API_BASE_URL:
            raise ValueError("E2E Telegram API traffic must use provider-simulator.")
        if self.telegram_bot_file_base_url != E2E_TELEGRAM_BOT_FILE_BASE_URL:
            raise ValueError("E2E Telegram file traffic must use provider-simulator.")
        if self.telegram_public_bot_base_url != E2E_TELEGRAM_PUBLIC_BOT_BASE_URL:
            raise ValueError("E2E Telegram linking must use provider-simulator.")
        if self.binance_spot_base_url != E2E_BINANCE_SPOT_BASE_URL:
            raise ValueError("E2E Binance REST traffic must use provider-simulator.")
        if self.binance_spot_ws_base_url != E2E_BINANCE_SPOT_WS_BASE_URL:
            raise ValueError("E2E Binance WebSocket traffic must use provider-simulator.")
        return self


class Settings(AuthenticationSettings):
    database_url: str

    @model_validator(mode="after")
    def validate_e2e_database(self) -> "Settings":
        if self.e2e_test_mode:
            database_name = self.database_url.split("?", 1)[0].rsplit("/", 1)[-1]
            if not database_name.endswith("_e2e"):
                raise ValueError("E2E_TEST_MODE requires a database name ending in _e2e.")
        return self


@lru_cache
def get_authentication_settings() -> AuthenticationSettings:
    return AuthenticationSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
