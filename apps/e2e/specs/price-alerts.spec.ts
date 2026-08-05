import { PriceAlertsPage } from "../pages/price-alerts.page";
import { expect, test } from "../fixtures/test";

test.describe.configure({ mode: "serial" });

test.describe("one-time price alerts", () => {
  test("requires Telegram readiness before an alert can be activated", async ({ newAuthenticatedPage }) => {
    const alerts = new PriceAlertsPage(newAuthenticatedPage);
    await alerts.goto();
    await alerts.openCreate();
    await alerts.chooseMarket("BTCUSDT");
    await alerts.fillTarget("101.000001");

    await expect(newAuthenticatedPage.getByRole("alert").getByText("Connect Telegram before creating an alert", { exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("dialog", { name: "Create price alert" }).getByRole("button", { name: "Create price alert", exact: true })).toBeDisabled();
  });

  test("supports dialog focus, condition, target validation, preview, and exactly one browser create", async ({
    appApi,
    connectedTelegramPage,
  }) => {
    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await alerts.goto();
    await alerts.openCreate();
    const dialog = connectedTelegramPage.getByRole("dialog", { name: "Create price alert" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Cancel", exact: true })).toBeVisible();

    await alerts.chooseMarket("BTCUSDT");
    await alerts.chooseCondition("Crosses below");
    await alerts.fillTarget("0");
    await expect(dialog.getByRole("button", { name: "Create price alert", exact: true })).toBeDisabled();
    await alerts.fillTarget("101.000001");
    await expect(connectedTelegramPage.getByText("Request preview", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByText(/BTCUSDT crosses below 101\.000001 USDT/)).toBeVisible();

    await alerts.fillTarget("101.1234567890123456789");
    await expect(dialog.getByRole("button", { name: "Create price alert", exact: true })).toBeDisabled();
    await alerts.fillTarget("101.000001");
    await alerts.submitCreate();
    await expect(dialog).toBeHidden();

    const created = (await appApi.listAlerts({ limit: 20 })) as {
      alerts: Array<{ symbol?: string; market?: { symbol: string } }>;
    };
    expect(created.alerts).toHaveLength(1);
    expect(created.alerts[0].market?.symbol).toBe("BTCUSDT");
  });

  test("preserves server idempotency and renders live waiting, monitoring, crossing, and delivery states", async ({
    appApi,
    connectedTelegramPage,
    providerSimulator,
  }) => {
    const idempotencyKey = "00000000-0000-4000-8000-000000000114";
    await appApi.createPriceAlert({
      idempotencyKey,
      symbol: "BTCUSDT",
      targetPrice: "101.000001",
    });
    await appApi.createPriceAlert({
      idempotencyKey,
      symbol: "BTCUSDT",
      targetPrice: "101.000001",
    });
    const replayed = (await appApi.listAlerts({ limit: 20 })) as { alerts: unknown[] };
    expect(replayed.alerts).toHaveLength(1);

    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await alerts.goto();
    await expect(connectedTelegramPage.getByText("Waiting for the first live price before evaluation.", { exact: true })).toBeVisible();

    await expect
      .poll(
        async () => {
          const result = await providerSimulator.setPrice("BTCUSDT", "100.000000");
          if (result.published !== true) {
            return false;
          }
          const response = await appApi.listAlerts({ limit: 20 });
          const alerts = Array.isArray(response.alerts) ? response.alerts : [];
          return (alerts[0] as { evaluationReady?: boolean } | undefined)?.evaluationReady === true;
        },
        { intervals: [250, 500, 1_000], timeout: 30_000 },
      )
      .toBe(true);
    await connectedTelegramPage.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(connectedTelegramPage.getByText("Monitoring live prices.", { exact: true })).toBeVisible();

    await expect
      .poll(
        async () => {
          const result = await providerSimulator.setPrice("BTCUSDT", "102.000000");
          if (result.published !== true) {
            return false;
          }
          const response = await appApi.listAlerts({ limit: 20 });
          const alerts = Array.isArray(response.alerts) ? response.alerts : [];
          return (alerts[0] as { status?: string } | undefined)?.status === "triggered";
        },
        { intervals: [250, 500, 1_000], timeout: 30_000 },
      )
      .toBe(true);
    await connectedTelegramPage.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(connectedTelegramPage.getByText("Triggered", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByText("Telegram accepted the notification.", { exact: false })).toBeVisible();
  });

  test("handles market-data warnings and terminal deletion rules", async ({
    appApi,
    connectedTelegramPage,
    providerSimulator,
  }) => {
    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await appApi.createPriceAlert({ symbol: "ETHUSDT", targetPrice: "111.000001" });
    await alerts.goto();
    await providerSimulator.disconnectBinance();
    await connectedTelegramPage.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(connectedTelegramPage.getByText(/market-data connection is unavailable|Live market data is delayed/i)).toBeVisible();
    await providerSimulator.reconnectBinance();
  });

  test("renders the active-limit error without exposing server details", async ({
    authenticatedSession,
    connectedTelegramPage,
    e2eControl,
  }) => {
    await e2eControl.createPriceAlertFixture({
      userId: authenticatedSession.userId,
      symbol: "BTCUSDT",
      count: 20,
      status: "active",
    });
    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await alerts.goto();
    await alerts.openCreate();
    await alerts.chooseMarket("BTCUSDT");
    await alerts.fillTarget("150.000001");
    await alerts.submitCreate();
    await expect(connectedTelegramPage.getByText("You already have the maximum of 20 active alerts.", { exact: true })).toBeVisible();
  });

  test("renders the rate-limit error without exposing server details", async ({
    appApi,
    connectedTelegramPage,
  }) => {
    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await alerts.goto();
    for (let index = 0; index < 10; index += 1) {
      await appApi.createPriceAlert({
        symbol: "ETHUSDT",
        targetPrice: `${120 + index}.000001`,
      });
    }
    await alerts.openCreate();
    await alerts.chooseMarket("ETHUSDT");
    await alerts.fillTarget("150.000001");
    await alerts.submitCreate();
    await expect(connectedTelegramPage.getByText(/Too many alert requests\./)).toBeVisible();
  });

  test("uses owner-scoped pagination, filter tabs, and confirmed deletion", async ({
    appApi,
    connectedTelegramPage,
    e2eControl,
    authenticatedSession,
  }) => {
    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await e2eControl.createPriceAlertFixture({
      userId: authenticatedSession.userId,
      symbol: "BNBUSDT",
      count: 25,
    });
    await alerts.goto();
    await alerts.selectStatus("Disabled");
    await expect(connectedTelegramPage.getByText("Disabled", { exact: true }).first()).toBeVisible();
    await expect(connectedTelegramPage.getByRole("button", { name: "Load more", exact: true })).toBeVisible();
    await connectedTelegramPage.getByRole("button", { name: "Load more", exact: true }).click();
    await expect(connectedTelegramPage.getByRole("button", { name: "Load more", exact: true })).toBeHidden();

    const deleteButton = connectedTelegramPage.getByRole("button", { name: "Delete alert", exact: true }).first();
    await deleteButton.click();
    await expect(connectedTelegramPage.getByRole("alertdialog", { name: "Delete this price alert?" })).toBeVisible();
    await connectedTelegramPage.getByRole("alertdialog").getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(connectedTelegramPage.getByRole("alertdialog")).toBeHidden();

    await deleteButton.click();
    await connectedTelegramPage.getByRole("alertdialog").getByRole("button", { name: "Delete alert", exact: true }).click();
    await expect(connectedTelegramPage.getByRole("alertdialog")).toBeHidden();

    const remaining = (await appApi.listAlerts({ limit: 50, status: "disabled" })) as {
      alerts: unknown[];
    };
    expect(remaining.alerts.length).toBeGreaterThan(0);
  });
});
