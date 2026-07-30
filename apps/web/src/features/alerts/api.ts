import type {
  CreatePriceAlertRequest,
  PriceAlertEnvelope,
  PriceAlertListEnvelope,
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

export function listPriceAlerts(cursor?: string): Promise<PriceAlertListEnvelope> {
  const query = new URLSearchParams({ limit: "20" });
  if (cursor) {
    query.set("cursor", cursor);
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
    body: JSON.stringify(request),
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
