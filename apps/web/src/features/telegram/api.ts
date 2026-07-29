import type {
  TelegramConnectionEnvelope,
  TelegramLinkResponse,
  TelegramTestNotificationEnvelope,
} from "./types";

type ApiErrorPayload = {
  code?: string;
  message?: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export class TelegramApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
    public readonly retryAfter?: string | null,
  ) {
    super("Telegram request failed.");
  }
}

function getApiUrl(path: string): string {
  if (!apiBaseUrl) {
    throw new Error("The browser API URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}

async function getApiError(response: Response): Promise<TelegramApiError> {
  let payload: ApiErrorPayload | undefined;

  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = undefined;
  }

  return new TelegramApiError(
    response.status,
    payload?.code,
    response.headers.get("Retry-After"),
  );
}

async function requestTelegram<T>(
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

export function getTelegramConnection(): Promise<TelegramConnectionEnvelope> {
  return requestTelegram<TelegramConnectionEnvelope>("/telegram/connection");
}

export function createTelegramLink(
  csrfToken: string,
): Promise<TelegramLinkResponse> {
  return requestTelegram<TelegramLinkResponse>("/telegram/link-tokens", {
    method: "POST",
    headers: {
      "X-CSRF-Token": csrfToken,
    },
  });
}

export function queueTelegramTestNotification(
  csrfToken: string,
  idempotencyKey: string,
): Promise<TelegramTestNotificationEnvelope> {
  return requestTelegram<TelegramTestNotificationEnvelope>(
    "/telegram/test-notifications",
    {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
        "X-CSRF-Token": csrfToken,
      },
    },
  );
}

export function getTelegramTestNotification(
  notificationId: string,
): Promise<TelegramTestNotificationEnvelope> {
  return requestTelegram<TelegramTestNotificationEnvelope>(
    `/telegram/test-notifications/${notificationId}`,
  );
}

export async function disconnectTelegram(csrfToken: string): Promise<void> {
  const response = await fetch(getApiUrl("/telegram/connection"), {
    method: "DELETE",
    credentials: "include",
    headers: {
      "X-CSRF-Token": csrfToken,
    },
  });

  if (!response.ok) {
    throw await getApiError(response);
  }
}
