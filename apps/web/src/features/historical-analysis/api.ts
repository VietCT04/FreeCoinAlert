import type {
  HistoricalAnalysisConfiguration,
  HistoricalAnalysisCoverage,
  HistoricalAnalysisCreateRequest,
  HistoricalAnalysisEquityEnvelope,
  HistoricalAnalysisReportEnvelope,
  HistoricalAnalysisRunEnvelope,
  HistoricalAnalysisRunListEnvelope,
  HistoricalAnalysisTradesEnvelope,
} from "./types";

type ApiErrorPayload = {
  code?: unknown;
  details?: unknown;
};

export type HistoricalAnalysisApiErrorDetail = {
  field: string;
  code: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export class HistoricalAnalysisApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
    public readonly retryAfter?: string | null,
    public readonly details: HistoricalAnalysisApiErrorDetail[] = [],
  ) {
    super("Historical analysis request failed.");
  }
}

function getApiUrl(path: string): string {
  if (!apiBaseUrl) {
    throw new Error("The browser API URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}

async function getApiError(response: Response): Promise<HistoricalAnalysisApiError> {
  let payload: ApiErrorPayload | undefined;

  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = undefined;
  }

  const details = Array.isArray(payload?.details)
    ? payload.details.flatMap((detail): HistoricalAnalysisApiErrorDetail[] => {
        if (!detail || typeof detail !== "object") {
          return [];
        }

        const field = (detail as { field?: unknown }).field;
        const code = (detail as { code?: unknown }).code;
        if (typeof field !== "string" || typeof code !== "string") {
          return [];
        }

        return [{ field, code }];
      })
    : [];

  return new HistoricalAnalysisApiError(
    response.status,
    typeof payload?.code === "string" ? payload.code : undefined,
    response.headers.get("Retry-After"),
    details,
  );
}

async function requestHistoricalAnalysis<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(getApiUrl(path), {
    ...options,
    credentials: "include",
  });

  if (!response.ok) {
    throw await getApiError(response);
  }

  return (await response.json()) as T;
}

export function getHistoricalAnalysisConfiguration(): Promise<HistoricalAnalysisConfiguration> {
  return requestHistoricalAnalysis<HistoricalAnalysisConfiguration>(
    "/historical-analysis/configuration",
  );
}

export function getHistoricalAnalysisCoverage(
  symbol: string,
  presetCode: string,
  presetVersion: number,
  signal?: AbortSignal,
): Promise<HistoricalAnalysisCoverage> {
  const query = new URLSearchParams({
    exchange: "binance",
    market_type: "spot",
    symbol,
    preset_code: presetCode,
    preset_version: String(presetVersion),
  });

  return requestHistoricalAnalysis<HistoricalAnalysisCoverage>(
    `/historical-analysis/coverage?${query.toString()}`,
    { signal },
  );
}

export function getHistoricalAnalyses(
  cursor?: string,
): Promise<HistoricalAnalysisRunListEnvelope> {
  const query = new URLSearchParams({ limit: "20" });
  if (cursor) {
    query.set("cursor", cursor);
  }

  return requestHistoricalAnalysis<HistoricalAnalysisRunListEnvelope>(
    `/historical-analyses?${query.toString()}`,
  );
}

export function getHistoricalAnalysis(
  runId: string,
): Promise<HistoricalAnalysisRunEnvelope> {
  return requestHistoricalAnalysis<HistoricalAnalysisRunEnvelope>(
    `/historical-analyses/${encodeURIComponent(runId)}`,
  );
}

export function createHistoricalAnalysis(
  csrfToken: string,
  idempotencyKey: string,
  request: HistoricalAnalysisCreateRequest,
): Promise<HistoricalAnalysisRunEnvelope> {
  return requestHistoricalAnalysis<HistoricalAnalysisRunEnvelope>(
    "/historical-analyses",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(request),
    },
  );
}

export function cancelHistoricalAnalysis(
  csrfToken: string,
  runId: string,
): Promise<HistoricalAnalysisRunEnvelope> {
  return requestHistoricalAnalysis<HistoricalAnalysisRunEnvelope>(
    `/historical-analyses/${encodeURIComponent(runId)}/cancel`,
    {
      method: "POST",
      headers: { "X-CSRF-Token": csrfToken },
    },
  );
}

export function getHistoricalAnalysisReport(
  runId: string,
): Promise<HistoricalAnalysisReportEnvelope> {
  return requestHistoricalAnalysis<HistoricalAnalysisReportEnvelope>(
    `/historical-analyses/${encodeURIComponent(runId)}/report`,
  );
}

export function getHistoricalAnalysisTrades(
  runId: string,
  cursor?: string,
): Promise<HistoricalAnalysisTradesEnvelope> {
  const query = new URLSearchParams({ limit: "50" });
  if (cursor) {
    query.set("cursor", cursor);
  }

  return requestHistoricalAnalysis<HistoricalAnalysisTradesEnvelope>(
    `/historical-analyses/${encodeURIComponent(runId)}/trades?${query.toString()}`,
  );
}

export function getHistoricalAnalysisEquity(
  runId: string,
  cursor?: string,
): Promise<HistoricalAnalysisEquityEnvelope> {
  const query = new URLSearchParams({ limit: "200" });
  if (cursor) {
    query.set("cursor", cursor);
  }

  return requestHistoricalAnalysis<HistoricalAnalysisEquityEnvelope>(
    `/historical-analyses/${encodeURIComponent(runId)}/equity?${query.toString()}`,
  );
}
