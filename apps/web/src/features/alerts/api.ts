import type {
  CreatePriceAlertRequest,
  PriceAlertEnvelope,
  PriceAlertListEnvelope,
  PriceAlertStatus,
} from "./types";

type ApiErrorPayload = { code?: string };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export class PriceAlertApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
    public readonly retryAfter?: string | null,
  ) {
    super("Price alert request failed.");
  }
}

function getApiUrl(path: string): string {
  if (!apiBaseUrl) {
    throw new Error("The browser API URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}

async function getApiError(response: Response): Promise<PriceAlertApiError> {
  let payload: ApiErrorPayload | undefined;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = undefined;
  }
  return new PriceAlertApiError(response.status, payload?.code, response.headers.get("Retry-After"));
}

async function requestAlerts<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(getApiUrl(path), { ...options, credentials: "include" });
  if (!response.ok) {
    throw await getApiError(response);
  }
  return (await response.json()) as T;
}

export type PriceAlertListOptions = {
  cursor?: string;
  limit?: number;
  status?: PriceAlertStatus;
};

export function listPriceAlerts(
  options: PriceAlertListOptions | string = {},
): Promise<PriceAlertListEnvelope> {
  const normalizedOptions =
    typeof options === "string" ? { cursor: options } : options;
  const query = new URLSearchParams({
    limit: String(normalizedOptions.limit ?? 20),
  });
  if (normalizedOptions.cursor) {
    query.set("cursor", normalizedOptions.cursor);
  }
  if (normalizedOptions.status) {
    query.set("status", normalizedOptions.status);
  }
  return requestAlerts<PriceAlertListEnvelope>(`/alerts?${query.toString()}`);
}

export function createPriceAlert(
  csrfToken: string,
  idempotencyKey: string,
  request: CreatePriceAlertRequest,
): Promise<PriceAlertEnvelope> {
  return requestAlerts<PriceAlertEnvelope>("/alerts/price", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey, "X-CSRF-Token": csrfToken },
    body: JSON.stringify({
      exchange: request.exchange,
      market_type: request.marketType,
      symbol: request.symbol,
      direction: request.direction,
      target_price: request.targetPrice,
    }),
  });
}

export async function deletePriceAlert(csrfToken: string, alertId: string): Promise<void> {
  const response = await fetch(getApiUrl(`/alerts/${alertId}`), {
    method: "DELETE",
    credentials: "include",
    headers: { "X-CSRF-Token": csrfToken },
  });
  if (!response.ok) {
    throw await getApiError(response);
  }
}
