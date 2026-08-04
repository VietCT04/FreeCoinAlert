import type { Page } from "@playwright/test";

export class PresetSignalsPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/preset-signals");
  }

  async openHistory(): Promise<void> {
    await this.page.getByRole("tab", { name: "Signal history", exact: true }).click();
  }

  async chooseMarket(symbol: string): Promise<void> {
    await this.page.locator("#signal-market").click();
    await this.page.getByRole("option", { name: new RegExp(symbol) }).click();
  }

  async chooseTimeframe(label: "All timeframes" | "1 hour" | "4 hours"): Promise<void> {
    await this.page.locator("#signal-timeframe-filter").click();
    await this.page.getByRole("option", { name: label, exact: true }).click();
  }

  async chooseSubscription(label: "All presets" | "Subscribed" | "Not subscribed"): Promise<void> {
    await this.page.locator("#signal-subscription-filter").click();
    await this.page.getByRole("option", { name: label, exact: true }).click();
  }
}
