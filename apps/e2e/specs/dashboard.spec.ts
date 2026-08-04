import { DashboardPage } from "../pages/dashboard.page";
import { expect, test } from "../fixtures/test";

test.describe.configure({ mode: "serial" });

test.describe("desktop dashboard shell", () => {
  test("renders landmarks, navigation, skip link, active route, and breadcrumbs", async ({
    checkAccessibility,
    newAuthenticatedPage,
  }) => {
    const dashboard = new DashboardPage(newAuthenticatedPage);
    await newAuthenticatedPage.goto("/dashboard");

    await expect(dashboard.heading()).toBeVisible();
    await expect(newAuthenticatedPage.locator("main#dashboard-main")).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("link", { name: "Skip to main content", exact: true })).toBeVisible();
    await expect(dashboard.routeLink("Overview")).toHaveAttribute("aria-current", "page");
    await expect(dashboard.routeLink("Price Alerts")).toBeVisible();
    await expect(dashboard.routeLink("Preset Signals")).toBeVisible();
    await expect(dashboard.routeLink("Historical Analysis")).toBeVisible();
    await expect(dashboard.routeLink("Telegram")).toBeVisible();

    await dashboard.routeLink("Price Alerts").click();
    await expect(newAuthenticatedPage).toHaveURL(/\/price-alerts$/);
    await expect(newAuthenticatedPage.getByRole("link", { name: "Overview", exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("link", { name: "Price Alerts", exact: true })).toHaveAttribute("aria-current", "page");

    await dashboard.openNavigation().click();
    await expect(newAuthenticatedPage.locator('[data-slot="sidebar"][data-state="collapsed"]')).toBeVisible();
    await dashboard.openNavigation().click();
    await expect(newAuthenticatedPage.locator('[data-slot="sidebar"][data-state="expanded"]')).toBeVisible();

    const accessibility = await checkAccessibility("desktop-dashboard-shell");
    expect(accessibility.violations).toEqual([]);
  });

  test("supports account-menu focus behavior and persistent light, dark, and system themes", async ({
    newAuthenticatedPage,
  }) => {
    const dashboard = new DashboardPage(newAuthenticatedPage);
    await newAuthenticatedPage.goto("/dashboard");

    await dashboard.accountMenu().click();
    await expect(newAuthenticatedPage.getByRole("menuitem", { name: "Sign out", exact: true })).toBeVisible();
    await newAuthenticatedPage.keyboard.press("Escape");
    await expect(newAuthenticatedPage.getByRole("menuitem", { name: "Sign out", exact: true })).toBeHidden();
    await expect(dashboard.accountMenu()).toBeFocused();

    for (const theme of ["Light", "Dark", "System"]) {
      await dashboard.themeMenu().click();
      await newAuthenticatedPage.getByRole("menuitemradio", { name: theme, exact: true }).click();
      await newAuthenticatedPage.reload();
      await expect(newAuthenticatedPage.locator("html")).toBeVisible();
    }
  });

  test("keeps the primary dashboard actions connected to their real routes", async ({ newAuthenticatedPage }) => {
    const dashboard = new DashboardPage(newAuthenticatedPage);
    await newAuthenticatedPage.goto("/dashboard");

    await expect(newAuthenticatedPage.getByRole("link", { name: "Create price alert", exact: true })).toHaveAttribute("href", "/price-alerts");
    await expect(newAuthenticatedPage.getByRole("link", { name: "Browse preset signals", exact: true })).toHaveAttribute("href", "/preset-signals");
    await expect(newAuthenticatedPage.getByRole("button", { name: "Refresh", exact: true })).toBeVisible();
    await expect(dashboard.heading()).toBeVisible();
  });

  test("shows empty and populated owner activity states", async ({
    appApi,
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await connectedTelegramPage.goto("/dashboard");
    await expect(connectedTelegramPage.getByRole("heading", { name: "No recent activity", exact: true })).toBeVisible();

    await appApi.createPriceAlert({ symbol: "BTCUSDT", targetPrice: "101.000001" });
    await connectedTelegramPage.goto("/price-alerts");
    await expect(connectedTelegramPage.getByText("Monitoring live prices.", { exact: true })).toBeVisible();
    await providerSimulator.setPrice("BTCUSDT", "100.000000");
    await providerSimulator.setPrice("BTCUSDT", "102.000000");
    await connectedTelegramPage.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(connectedTelegramPage.getByText("Triggered", { exact: true })).toBeVisible();

    await connectedTelegramPage.goto("/dashboard");
    await expect(connectedTelegramPage.getByText("Price alert triggered", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByRole("button", { name: "Refresh", exact: true })).toBeVisible();
  });
});
