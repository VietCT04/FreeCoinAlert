import type {
  HistoricalAnalysisConfiguration,
  HistoricalAnalysisCreateRequest,
  HistoricalAnalysisEquityEnvelope,
  HistoricalAnalysisReportEnvelope,
  HistoricalAnalysisRunEnvelope,
  HistoricalAnalysisRunListEnvelope,
  HistoricalAnalysisTradesEnvelope,
} from "./types";

type ApiErrorPayload = {
  code?: unknown;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export class HistoricalAnalysisApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
    public readonly retryAfter?: string | null,
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

  return new HistoricalAnalysisApiError(
    response.status,
    typeof payload?.code === "string" ? payload.code : undefined,
    response.headers.get("Retry-After"),
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
