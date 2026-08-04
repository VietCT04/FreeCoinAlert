import type { Page } from "@playwright/test";

export class TelegramPage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/telegram");
  }

  async refresh(): Promise<void> {
    await this.page.getByRole("button", { name: "Refresh status", exact: true }).click();
  }

  async createLink(): Promise<Page> {
    const popupPromise = this.page.waitForEvent("popup");
    await this.page
      .getByRole("button", { name: /^(Connect Telegram|Create new link)$/ })
      .click();
    const popup = await popupPromise;
    await popup.waitForLoadState("domcontentloaded");
    return popup;
  }

  async sendTest(): Promise<void> {
    await this.page
      .getByRole("button", { name: "Send test notification", exact: true })
      .click();
  }

  async confirmDisconnect(): Promise<void> {
    await this.page
      .getByRole("button", { name: "Disconnect Telegram", exact: true })
      .click();
    await this.page
      .getByRole("alertdialog")
      .getByRole("button", { name: "Disconnect Telegram", exact: true })
      .click();
  }
}
