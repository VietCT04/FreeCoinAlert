import { SignalApiError, type SignalApiErrorPayload } from "./errors";
import type {
  EnableSignalSubscriptionRequest,
  SignalFeedEnvelope,
  SignalPresetEnvelope,
  SignalSubscriptionEnvelope,
  SignalSubscriptionListEnvelope,
} from "./types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function getApiUrl(path: string): string {
  if (!apiBaseUrl) {
    throw new Error("The browser API URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}

async function getApiError(response: Response): Promise<SignalApiError> {
  let payload: SignalApiErrorPayload | undefined;

  try {
    payload = (await response.json()) as SignalApiErrorPayload;
  } catch {
    payload = undefined;
  }

  return new SignalApiError(
    response.status,
    payload?.code,
    response.headers.get("Retry-After"),
  );
}

async function requestSignals<T>(
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

export function getSignalPresets(): Promise<SignalPresetEnvelope> {
  return requestSignals<SignalPresetEnvelope>("/signal-presets");
}

export function getSignalSubscriptions(): Promise<SignalSubscriptionListEnvelope> {
  return requestSignals<SignalSubscriptionListEnvelope>("/signal-subscriptions");
}

export function enableSignalSubscription(
  csrfToken: string,
  request: EnableSignalSubscriptionRequest,
): Promise<SignalSubscriptionEnvelope> {
  return requestSignals<SignalSubscriptionEnvelope>("/signal-subscriptions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(request),
  });
}

export async function disableSignalSubscription(
  csrfToken: string,
  subscriptionId: string,
): Promise<void> {
  const response = await fetch(
    getApiUrl(`/signal-subscriptions/${encodeURIComponent(subscriptionId)}`),
    {
      method: "DELETE",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken },
    },
  );

  if (!response.ok) {
    throw await getApiError(response);
  }
}

export function getSignalFeed(cursor?: string): Promise<SignalFeedEnvelope> {
  const query = new URLSearchParams({ limit: "50" });
  if (cursor) {
    query.set("cursor", cursor);
  }

  return requestSignals<SignalFeedEnvelope>(`/signal-feed?${query.toString()}`);
}

export function getSignalStreamUrl(streamCursor: string): string {
  const query = new URLSearchParams({ after: streamCursor });
  return getApiUrl(`/signal-feed/stream?${query.toString()}`);
}
