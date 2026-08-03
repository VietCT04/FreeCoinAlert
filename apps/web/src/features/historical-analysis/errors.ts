import { HistoricalAnalysisApiError } from "./api";

export function isHistoricalAnalysisAuthenticationError(
  error: unknown,
): boolean {
  return (
    error instanceof HistoricalAnalysisApiError &&
    (error.status === 401 || error.code === "AUTHENTICATION_REQUIRED")
  );
}

function retryAfterMessage(error: HistoricalAnalysisApiError): string {
  return error.retryAfter
    ? ` Try again in ${error.retryAfter} seconds.`
    : " Please try again later.";
}

export function historicalAnalysisErrorMessage(error: unknown): string {
  if (error instanceof HistoricalAnalysisApiError) {
    switch (error.code) {
      case "HISTORICAL_ANALYSIS_REQUEST_INVALID":
        return "That historical-analysis request is invalid. Review the market, preset, and UTC date range.";
      case "HISTORICAL_ANALYSIS_MARKET_NOT_FOUND":
        return "That market is no longer available for historical analysis. Refresh the market list.";
      case "HISTORICAL_ANALYSIS_PRESET_NOT_FOUND":
        return "That preset version is no longer available. Refresh the preset list.";
      case "HISTORICAL_ANALYSIS_PRESET_UNAVAILABLE":
        return "That preset is not available for historical analysis.";
      case "HISTORICAL_ANALYSIS_RANGE_UNAVAILABLE":
        return "That UTC range is outside the available historical-analysis limits or stored coverage.";
      case "HISTORICAL_ANALYSIS_ACTIVE_LIMIT_REACHED":
        return "You already have the maximum number of queued or running analyses.";
      case "HISTORICAL_ANALYSIS_IDEMPOTENCY_CONFLICT":
        return "This submission key is already associated with a different analysis. Start a new analysis to continue.";
      case "HISTORICAL_ANALYSIS_NOT_FOUND":
        return "This historical analysis or report is no longer available.";
      case "HISTORICAL_ANALYSIS_REPORT_NOT_READY":
        return "The report is not ready yet. Refresh the selected analysis after it completes.";
      case "HISTORICAL_ANALYSIS_RATE_LIMITED":
        return `Too many historical-analysis requests.${retryAfterMessage(error)}`;
      case "HISTORICAL_ANALYSIS_UNAVAILABLE":
        return "Historical analysis is temporarily unavailable. Please try again.";
      case "AUTHENTICATION_REQUIRED":
        return "Your session has ended. Please sign in again.";
      case "AUTH_CSRF_INVALID":
        return "Your session could not be confirmed. Refresh the page and try again.";
      default:
        if (error.status === 429) {
          return `Too many historical-analysis requests.${retryAfterMessage(error)}`;
        }
        break;
    }
  }

  return "We couldn't complete that historical-analysis request. Please try again.";
}

export function historicalAnalysisFailureMessage(
  failureCode: string | null,
): string | null {
  switch (failureCode) {
    case null:
      return null;
    case "historical_dataset_insufficient_warmup":
      return "There is not enough complete stored candle history for the required warm-up period.";
    case "historical_dataset_gap_detected":
      return "Stored candle history contains a gap in the selected analysis coverage.";
    case "historical_dataset_incomplete":
      return "Stored candle history is incomplete for the selected range.";
    case "historical_dataset_invalid":
      return "Stored candle history could not be validated for this analysis.";
    case "historical_dataset_stale":
      return "Stored candle history changed before the report was published. Create a new analysis to use the latest revisions.";
    case "historical_dataset_too_large":
      return "This analysis exceeds the stored historical-data limit.";
    case "historical_simulation_invalid_input":
      return "The fixed simulation could not use the selected historical input.";
    case "historical_simulation_unsupported_version":
      return "This analysis uses a simulation version that is no longer supported.";
    case "historical_analysis_attempts_exhausted":
      return "Historical analysis could not be completed after its bounded recovery attempts.";
    case "historical_analysis_engine_failure":
    case "historical_analysis_persistence_failure":
    case "historical_analysis_unavailable":
    case "historical_analysis_result_conflict":
      return "Historical analysis could not be completed. Please create a new analysis.";
    default:
      return "Historical analysis failed with a safe server failure category. Please create a new analysis.";
  }
}
