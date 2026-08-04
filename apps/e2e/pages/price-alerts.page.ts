import type { Page } from "@playwright/test";

export class PriceAlertsPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/price-alerts");
  }

  async openCreate(): Promise<void> {
    await this.page.getByRole("button", { name: "Create alert", exact: true }).click();
  }

  async cancelCreate(): Promise<void> {
    await this.page
      .getByRole("dialog", { name: "Create price alert" })
      .getByRole("button", { name: "Cancel", exact: true })
      .click();
  }

  async chooseMarket(symbol: string): Promise<void> {
    await this.page.locator("#price-alert-market").click();
    await this.page.getByRole("option", { name: new RegExp(symbol) }).click();
  }

  async chooseCondition(label: "Crosses above" | "Crosses below"): Promise<void> {
    await this.page.locator("#price-alert-direction").click();
    await this.page.getByRole("option", { name: label, exact: true }).click();
  }

  async fillTarget(value: string): Promise<void> {
    await this.page.getByLabel("Target price", { exact: true }).fill(value);
  }

  async submitCreate(): Promise<void> {
    await this.page
      .getByRole("dialog", { name: "Create price alert" })
      .getByRole("button", { name: "Create price alert", exact: true })
      .click();
  }

  async selectStatus(label: string): Promise<void> {
    await this.page.getByRole("tab", { name: label, exact: true }).click();
  }
}
