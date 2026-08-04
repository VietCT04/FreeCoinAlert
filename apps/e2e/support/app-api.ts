import { randomUUID } from "node:crypto";
import type { APIRequestContext, StorageState } from "@playwright/test";

import type { TestUser } from "../fixtures/users";

type AuthResponse = {
  user: { id: string; email: string; createdAt: string };
  csrfToken: string;
};

type RequestOptions = {
  headers?: Record<string, string>;
};

export class AppApi {
  private csrfToken: string | null = null;
  private userId: string | null = null;

  constructor(private readonly request: APIRequestContext) {}

  async register(user: TestUser): Promise<AuthResponse> {
    const response = await this.request.post("/auth/register", {
      data: { email: user.email, password: user.password },
    });
    const payload = await this.read<AuthResponse>(response, 201);
    this.setAuth(payload);
    return payload;
  }

  async signIn(user: TestUser): Promise<AuthResponse> {
    const response = await this.request.post("/auth/login", {
      data: { email: user.email, password: user.password },
    });
    const payload = await this.read<AuthResponse>(response, 200);
    this.setAuth(payload);
    return payload;
  }

  async currentUser(): Promise<AuthResponse> {
    const response = await this.request.get("/auth/me");
    const payload = await this.read<AuthResponse>(response, 200);
    this.setAuth(payload);
    return payload;
  }

  async signOut(): Promise<void> {
    const response = await this.request.post("/auth/logout", {
      headers: this.csrfHeaders(),
    });
    await this.read<void>(response, 204);
    this.csrfToken = null;
    this.userId = null;
  }

  async storageState(): Promise<StorageState> {
    return this.request.storageState();
  }

  get ownerId(): string {
    if (!this.userId) {
      throw new Error("The E2E API session is not authenticated.");
    }
    return this.userId;
  }

  get csrf(): string {
    if (!this.csrfToken) {
      throw new Error("The E2E API session has no CSRF token.");
    }
    return this.csrfToken;
  }

  getMarkets(): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>("/markets");
  }

  getTelegramConnection(): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>("/telegram/connection");
  }

  createTelegramLink(): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>("/telegram/link-tokens", undefined, this.csrfHeaders());
  }

  queueTelegramTest(idempotencyKey: string): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(
      "/telegram/test-notifications",
      undefined,
      { ...this.csrfHeaders(), "Idempotency-Key": idempotencyKey },
    );
  }

  getTelegramTest(notificationId: string): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(`/telegram/test-notifications/${notificationId}`);
  }

  async disconnectTelegram(): Promise<void> {
    const response = await this.request.delete("/telegram/connection", {
      headers: this.csrfHeaders(),
    });
    await this.read<void>(response, 204);
  }

  listAlerts(options: {
    limit?: number;
    status?: string;
    cursor?: string;
  } = {}): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      this.withQuery("/alerts", {
        limit: options.limit ?? 20,
        status: options.status,
        cursor: options.cursor,
      }),
    );
  }

  createPriceAlert(input: {
    symbol: string;
    direction?: "cross_above" | "cross_below";
    targetPrice?: string;
    idempotencyKey?: string;
  }): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(
      "/alerts/price",
      {
        exchange: "binance",
        market_type: "spot",
        symbol: input.symbol,
        direction: input.direction ?? "cross_above",
        target_price: input.targetPrice ?? "101.000000",
      },
      {
        ...this.csrfHeaders(),
        "Idempotency-Key": input.idempotencyKey ?? randomUUID(),
      },
    );
  }

  async deleteAlert(alertId: string): Promise<void> {
    const response = await this.request.delete(`/alerts/${encodeURIComponent(alertId)}`, {
      headers: this.csrfHeaders(),
    });
    await this.read<void>(response, 204);
  }

  getPresets(): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>("/signal-presets");
  }

  getSignalSubscriptions(): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>("/signal-subscriptions");
  }

  subscribe(input: {
    symbol: string;
    presetCode: string;
    presetVersion: number;
  }): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(
      "/signal-subscriptions",
      {
        exchange: "binance",
        market_type: "spot",
        symbol: input.symbol,
        preset_code: input.presetCode,
        preset_version: input.presetVersion,
      },
      this.csrfHeaders(),
    );
  }

  async disableSubscription(subscriptionId: string): Promise<void> {
    const response = await this.request.delete(
      `/signal-subscriptions/${encodeURIComponent(subscriptionId)}`,
      { headers: this.csrfHeaders() },
    );
    await this.read<void>(response, 204);
  }

  setSignalTelegramDelivery(
    subscriptionId: string,
    enabled: boolean,
  ): Promise<Record<string, unknown>> {
    return this.put<Record<string, unknown>>(
      `/signal-subscriptions/${encodeURIComponent(subscriptionId)}/telegram-delivery`,
      { enabled },
      this.csrfHeaders(),
    );
  }

  getSignalFeed(options: {
    limit?: number;
    status?: "current" | "invalidated" | "all";
    cursor?: string;
  } = {}): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      this.withQuery("/signal-feed", {
        limit: options.limit ?? 50,
        status: options.status ?? "current",
        cursor: options.cursor,
      }),
    );
  }

  getHistoricalConfiguration(): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>("/historical-analysis/configuration");
  }

  listHistoricalAnalyses(options: {
    limit?: number;
    status?: string;
    cursor?: string;
  } = {}): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      this.withQuery("/historical-analyses", {
        limit: options.limit ?? 20,
        status: options.status,
        cursor: options.cursor,
      }),
    );
  }

  getHistoricalAnalysis(runId: string): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      `/historical-analyses/${encodeURIComponent(runId)}`,
    );
  }

  createHistoricalAnalysis(input: {
    symbol: string;
    presetCode: string;
    presetVersion: number;
    analysisStart: string;
    analysisEnd: string;
    idempotencyKey?: string;
  }): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(
      "/historical-analyses",
      {
        exchange: "binance",
        market_type: "spot",
        symbol: input.symbol,
        preset_code: input.presetCode,
        preset_version: input.presetVersion,
        analysis_start: input.analysisStart,
        analysis_end: input.analysisEnd,
      },
      {
        ...this.csrfHeaders(),
        "Idempotency-Key": input.idempotencyKey ?? randomUUID(),
      },
    );
  }

  cancelHistoricalAnalysis(runId: string): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(
      `/historical-analyses/${encodeURIComponent(runId)}/cancel`,
      undefined,
      this.csrfHeaders(),
    );
  }

  getHistoricalReport(runId: string): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      `/historical-analyses/${encodeURIComponent(runId)}/report`,
    );
  }

  getHistoricalTrades(
    runId: string,
    cursor?: string,
  ): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      this.withQuery(`/historical-analyses/${encodeURIComponent(runId)}/trades`, {
        limit: 50,
        cursor,
      }),
    );
  }

  getHistoricalEquity(
    runId: string,
    cursor?: string,
  ): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(
      this.withQuery(`/historical-analyses/${encodeURIComponent(runId)}/equity`, {
        limit: 200,
        cursor,
      }),
    );
  }

  private async get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await this.request.get(path, options);
    return this.read<T>(response, 200);
  }

  private async post<T>(
    path: string,
    data?: Record<string, unknown>,
    headers?: Record<string, string>,
  ): Promise<T> {
    const response = await this.request.post(path, { data, headers });
    return this.read<T>(response, 200, 201);
  }

  private async put<T>(
    path: string,
    data: Record<string, unknown>,
    headers?: Record<string, string>,
  ): Promise<T> {
    const response = await this.request.put(path, { data, headers });
    return this.read<T>(response, 200);
  }

  private async read<T>(
    response: { ok(): boolean; status(): number; json(): Promise<unknown> },
    ...expected: number[],
  ): Promise<T> {
    if (!response.ok() || !expected.includes(response.status())) {
      throw new Error("The E2E application API request failed.");
    }
    if (response.status() === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  private setAuth(payload: AuthResponse): void {
    this.csrfToken = payload.csrfToken;
    this.userId = payload.user.id;
  }

  private csrfHeaders(): Record<string, string> {
    return { "X-CSRF-Token": this.csrf };
  }

  private withQuery(
    path: string,
    values: Record<string, string | number | undefined>,
  ): string {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(values)) {
      if (value !== undefined) {
        query.set(key, String(value));
      }
    }
    return `${path}?${query.toString()}`;
  }
}
