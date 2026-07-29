import type { AuthenticationResponse } from "./types";

type ApiErrorPayload = {
  code?: string;
  message?: string;
  details?: unknown[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export class AuthApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
    public readonly retryAfter?: string | null,
  ) {
    super("Authentication request failed.");
  }
}

function getApiUrl(path: string): string {
  if (!apiBaseUrl) {
    throw new Error("The browser API URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}

async function getApiError(response: Response): Promise<AuthApiError> {
  let payload: ApiErrorPayload | undefined;

  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = undefined;
  }

  return new AuthApiError(
    response.status,
    payload?.code,
    response.headers.get("Retry-After"),
  );
}

async function requestAuthentication<T>(
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

export function getCurrentUser(): Promise<AuthenticationResponse> {
  return requestAuthentication<AuthenticationResponse>("/auth/me");
}

export function registerAccount(
  email: string,
  password: string,
): Promise<AuthenticationResponse> {
  return requestAuthentication<AuthenticationResponse>("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
}

export function signIn(
  email: string,
  password: string,
): Promise<AuthenticationResponse> {
  return requestAuthentication<AuthenticationResponse>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
}

export async function signOut(csrfToken: string): Promise<void> {
  const response = await fetch(getApiUrl("/auth/logout"), {
    method: "POST",
    credentials: "include",
    headers: {
      "X-CSRF-Token": csrfToken,
    },
  });

  if (!response.ok) {
    throw await getApiError(response);
  }
}
