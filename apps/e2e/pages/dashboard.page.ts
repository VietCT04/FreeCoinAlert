import type { Locator, Page } from "@playwright/test";

export class DashboardPage {
  constructor(private readonly page: Page) {}

  heading(): Locator {
    return this.page.getByRole("heading", { name: "Overview", exact: true });
  }

  routeLink(label: string): Locator {
    return this.page.locator('[data-sidebar="sidebar"]').getByRole("link", {
      name: label,
      exact: true,
    });
  }

  navigationLinks(): Locator {
    return this.page.locator('[data-sidebar="sidebar"] a');
  }

  openNavigation(): Locator {
    return this.page.getByRole("button", { name: "Open navigation", exact: true });
  }

  accountMenu(): Locator {
    return this.page.getByRole("button", { name: "Open account menu", exact: true });
  }

  themeMenu(): Locator {
    return this.page.getByRole("button", { name: "Choose color theme", exact: true });
  }
}
