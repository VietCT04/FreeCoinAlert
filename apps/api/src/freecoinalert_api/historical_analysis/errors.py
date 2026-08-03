from freecoinalert_api.api.errors import AuthenticationError


class HistoricalAnalysisError(AuthenticationError):
    """Safe API error for historical-analysis request and lifecycle operations."""


def request_invalid_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=422,
        code="HISTORICAL_ANALYSIS_REQUEST_INVALID",
        message="The historical-analysis request is invalid.",
    )


def market_not_found_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=404,
        code="HISTORICAL_ANALYSIS_MARKET_NOT_FOUND",
        message="The requested historical-analysis market was not found.",
    )


def preset_not_found_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=404,
        code="HISTORICAL_ANALYSIS_PRESET_NOT_FOUND",
        message="The requested historical-analysis preset was not found.",
    )


def preset_unavailable_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=409,
        code="HISTORICAL_ANALYSIS_PRESET_UNAVAILABLE",
        message="The requested historical-analysis preset is unavailable.",
    )


def range_unavailable_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=409,
        code="HISTORICAL_ANALYSIS_RANGE_UNAVAILABLE",
        message="The requested historical-analysis range is unavailable.",
    )


def active_limit_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=409,
        code="HISTORICAL_ANALYSIS_ACTIVE_LIMIT_REACHED",
        message="The active historical-analysis run limit has been reached.",
    )


def idempotency_conflict_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=409,
        code="HISTORICAL_ANALYSIS_IDEMPOTENCY_CONFLICT",
        message="The Idempotency-Key was already used for a different historical analysis.",
    )


def not_found_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=404,
        code="HISTORICAL_ANALYSIS_NOT_FOUND",
        message="The historical-analysis run was not found.",
    )


def unavailable_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=503,
        code="HISTORICAL_ANALYSIS_UNAVAILABLE",
        message="Historical analysis is temporarily unavailable.",
    )


def report_not_ready_error() -> HistoricalAnalysisError:
    return HistoricalAnalysisError(
        status_code=409,
        code="HISTORICAL_ANALYSIS_REPORT_NOT_READY",
        message="The historical-analysis report is not ready.",
    )
