import type { Locator, Page } from "@playwright/test";

export class DashboardPage {
  constructor(private readonly page: Page) {}

  heading(): Locator {
    return this.page.getByRole("heading", { name: "Overview", exact: true });
  }
}
