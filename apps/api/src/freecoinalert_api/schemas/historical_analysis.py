import uuid
from datetime import datetime
from typing import Any, Literal

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


class HistoricalAnalysisReportSummaryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    analysis_candle_count: int
    signal_count: int
    trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    overlapping_signal_count: int
    insufficient_forward_signal_count: int
    equity_exhausted_signal_count: int
    initial_equity: str
    final_equity: str
    gross_return: str
    net_return: str
    maximum_drawdown: str
    win_rate: str | None
    win_rate_undefined_reason: str | None
    profit_factor: str | None
    profit_factor_undefined_reason: str | None


class HistoricalAnalysisTradeResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    sequence: int
    signal_candle_id: uuid.UUID
    signal_candle_revision: int
    signal_open_time: datetime
    signal_close_time: datetime
    signal_direction: str
    position_direction: str
    entry_candle_id: uuid.UUID
    entry_candle_revision: int
    entry_open_time: datetime
    entry_raw_price: str
    entry_fill_price: str
    exit_candle_id: uuid.UUID
    exit_candle_revision: int
    exit_close_time: datetime
    exit_raw_price: str
    exit_fill_price: str
    holding_candle_count: int
    fee_rate: str
    slippage_rate: str
    equity_before: str
    gross_return: str
    net_return: str
    gross_pnl: str
    net_pnl: str
    equity_after: str
    outcome: str


class HistoricalAnalysisEquityPointResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    sequence: int
    candle_id: uuid.UUID
    candle_revision: int
    candle_open_time: datetime
    candle_close_time: datetime
    equity: str
    drawdown: str
    position_state: str
    active_trade_sequence: int | None


class HistoricalAnalysisReportResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    report_id: uuid.UUID
    run_id: uuid.UUID
    dataset_id: uuid.UUID
    market: HistoricalAnalysisMarketSnapshotResponse
    preset: HistoricalAnalysisPresetSnapshotResponse
    calculation_version: str
    engine_version: str
    assumption_version: str
    result_fingerprint: str
    dataset_fingerprint: str
    analysis_start: datetime
    analysis_end: datetime
    coverage: dict[str, Any]
    assumptions: dict[str, Any]
    summary: HistoricalAnalysisReportSummaryResponse
    safety_disclosures: list[str]
    equity_preview: list[HistoricalAnalysisEquityPointResponse]
    trades_available: bool
    equity_available: bool
    trades_path: str
    equity_path: str


class HistoricalAnalysisReportEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    report: HistoricalAnalysisReportResponse


class HistoricalAnalysisTradesEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    trades: list[HistoricalAnalysisTradeResponse]
    next_cursor: str | None


class HistoricalAnalysisEquityEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    equity: list[HistoricalAnalysisEquityPointResponse]
    next_cursor: str | None
