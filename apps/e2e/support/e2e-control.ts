import type { APIRequestContext } from "@playwright/test";

type MutationResponse = {
  accepted?: boolean;
  sequence?: number;
  [key: string]: unknown;
};

export type HistoricalFixtureScenario =
  | "success"
  | "zero_trade"
  | "pagination"
  | "terminal_failure";

export class E2EControl {
  private readonly baseUrl = "http://e2e-control:9100";

  constructor(private readonly request: APIRequestContext) {}

  async reset() {
    return this.mutate("/__e2e/reset");
  }

  async gateHistoricalWorker() {
    return this.mutate("/__e2e/historical-worker/gates", {
      names: ["historical_analysis_before_run"],
    });
  }

  async releaseHistoricalWorker() {
    return this.mutate("/__e2e/historical-worker/release", {
      names: ["historical_analysis_before_run"],
    });
  }

  async createHistoricalFixture(input: {
    userId: string;
    scenario?: HistoricalFixtureScenario;
    symbol?: string;
    presetCode?: string;
    presetVersion?: number;
    tradeCount?: number;
  }) {
    return this.mutate("/__e2e/fixtures/historical-analysis", input);
  }

  async expireTelegramLink(userId: string) {
    return this.mutate("/__e2e/fixtures/expire-telegram-link", { userId });
  }

  async createPriceAlertFixture(input: {
    userId: string;
    symbol?: string;
    count?: number;
    status?: "active" | "disabled";
  }) {
    return this.mutate("/__e2e/fixtures/price-alerts", input);
  }

  async createSignalFeedFixture(input: {
    userId: string;
    symbol?: string;
    presetCode?: string;
    presetVersion?: number;
    count?: number;
    invalidatedCount?: number;
  }) {
    return this.mutate("/__e2e/fixtures/signal-feed", input);
  }

  private async mutate(path: string, data?: Record<string, unknown>): Promise<MutationResponse> {
    const response = await this.request.post(`${this.baseUrl}${path}`, {
      headers: this.headers(),
      data,
    });
    if (!response.ok()) {
      throw new Error("The E2E control request failed.");
    }

    const payload = (await response.json()) as MutationResponse;
    if (payload.accepted !== true || !Number.isInteger(payload.sequence)) {
      throw new Error("The E2E control did not acknowledge its sequence.");
    }
    return payload;
  }

  private headers(): Record<string, string> {
    return { "X-E2E-Control-Token": process.env.E2E_CONTROL_TOKEN || "" };
  }
}
