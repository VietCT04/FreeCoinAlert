import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from freecoinalert_api.schemas.auth import to_camel_case


class HistoricalAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: StrictStr
    market_type: StrictStr
    symbol: StrictStr
    preset_code: StrictStr
    preset_version: StrictInt
    analysis_start: datetime
    analysis_end: datetime


class HistoricalAnalysisAssumptionsResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    signal_timing: Literal["confirmed_candle_close"]
    entry_timing: Literal["next_candle_open"]
    holding_period_candles: int
    fee_bps_per_side: str
    slippage_bps_per_side: str
    position_sizing: Literal["one_position_full_equity"]
    overlapping_signals: Literal["ignored"]
    end_of_range: Literal["incomplete_trade_not_opened"]


class HistoricalAnalysisConfigurationResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    minimum_range_days: int
    maximum_range_days: int
    maximum_active_runs: int
    simulation_version: str
    assumption_version: str
    assumptions: HistoricalAnalysisAssumptionsResponse


class HistoricalAnalysisMarketSnapshotResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    exchange: str
    market_type: str
    symbol: str
    base_asset: str
    quote_asset: str


class HistoricalAnalysisPresetParametersResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    period: int
    threshold: str | None
    price_input: str


class HistoricalAnalysisPresetSnapshotResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    code: str
    version: int
    name: str
    strategy_type: str
    timeframe: str
    direction: str
    parameters: HistoricalAnalysisPresetParametersResponse


HistoricalAnalysisStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
]


class HistoricalAnalysisRunResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    id: uuid.UUID
    status: HistoricalAnalysisStatus
    market: HistoricalAnalysisMarketSnapshotResponse
    preset: HistoricalAnalysisPresetSnapshotResponse
    calculation_version: str
    simulation_version: str
    assumption_version: str
    analysis_start: datetime
    analysis_end: datetime
    progress_stage: str
    progress_percent: int
    cancellation_requested: bool
    cancellation_requested_at: datetime | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    failure_code: str | None


class HistoricalAnalysisRunEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    run: HistoricalAnalysisRunResponse


class HistoricalAnalysisRunListEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    runs: list[HistoricalAnalysisRunResponse]
    next_cursor: str | None

