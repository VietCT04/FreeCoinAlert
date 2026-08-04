import type { APIRequestContext } from "@playwright/test";

type MutationResponse = {
  accepted?: boolean;
  sequence?: number;
  [key: string]: unknown;
};

export type TelegramOutcome =
  | "sent"
  | "temporary_failure"
  | "permanent_failure"
  | "rate_limited"
  | "uncertain";

export class ProviderControl {
  private readonly baseUrl = "http://provider-simulator:9000";

  constructor(private readonly request: APIRequestContext) {}

  async reset(options: { unavailableSymbols?: string[]; outcomes?: TelegramOutcome[] } = {}) {
    return this.mutate("/__e2e/reset", options);
  }

  async setPrice(symbol: string, price: string) {
    return this.mutate("/__e2e/binance/price", { symbol, price });
  }

  async setKline(input: {
    symbol: string;
    openTimeMs?: number;
    openPrice?: string;
    closePrice?: string;
    highPrice?: string;
    lowPrice?: string;
    closed?: boolean;
  }) {
    return this.mutate("/__e2e/binance/kline", input);
  }

  async publishClosedKlineRange(input: {
    symbol: string;
    startTimeMs: number;
    count: number;
    openPrice: string;
    closePrice: string;
    highPrice?: string;
    lowPrice?: string;
  }) {
    for (let index = 0; index < input.count; index += 1) {
      await this.setKline({
        symbol: input.symbol,
        openTimeMs: input.startTimeMs + index * 60_000,
        openPrice: input.openPrice,
        closePrice: input.closePrice,
        highPrice: input.highPrice ?? input.closePrice,
        lowPrice: input.lowPrice ?? input.openPrice,
        closed: true,
      });
    }
  }

  async disconnectBinance() {
    return this.mutate("/__e2e/binance/disconnect");
  }

  async reconnectBinance() {
    return this.mutate("/__e2e/binance/reconnect");
  }

  async queueTelegramStart(token: string, chatId = 700000001) {
    return this.mutate("/__e2e/telegram/update", { token, chatId });
  }

  async queueTelegramOutcomes(outcomes: TelegramOutcome[]) {
    return this.mutate("/__e2e/telegram/outcomes", { outcomes });
  }

  async getTelegramMessages(): Promise<Record<string, unknown>> {
    const response = await this.request.get(`${this.baseUrl}/__e2e/telegram/messages`, {
      headers: this.headers(),
    });
    if (!response.ok()) {
      throw new Error("The E2E Telegram message control request failed.");
    }
    return (await response.json()) as Record<string, unknown>;
  }

  private async mutate(path: string, data?: Record<string, unknown>): Promise<MutationResponse> {
    const response = await this.request.post(`${this.baseUrl}${path}`, {
      headers: this.headers(),
      data,
    });
    if (!response.ok()) {
      throw new Error("The E2E provider control request failed.");
    }

    const payload = (await response.json()) as MutationResponse;
    if (payload.accepted !== true || !Number.isInteger(payload.sequence)) {
      throw new Error("The E2E provider control did not acknowledge its sequence.");
    }
    return payload;
  }

  private headers(): Record<string, string> {
    return { "X-E2E-Control-Token": process.env.E2E_CONTROL_TOKEN || "" };
  }
}
