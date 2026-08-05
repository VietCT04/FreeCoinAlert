import { expect, test } from "../fixtures/test";
import { PresetSignalsPage } from "../pages/preset-signals.page";
import { TelegramPage } from "../pages/telegram.page";
import { E2E_API_ORIGIN, E2E_WEB_ORIGIN } from "../support/urls";

test.describe.configure({ mode: "serial" });
test.setTimeout(120_000);

test.describe("session, provider, and live-feed recovery", () => {
  test.afterEach(async ({ e2eControl }) => {
    await e2eControl.reset();
  });

  test("redirects after session revocation and does not retain owner state", async ({
    appApi,
    playwright,
    newAuthenticatedPage,
  }) => {
    await newAuthenticatedPage.goto("/historical-analysis");
    await expect(newAuthenticatedPage.getByRole("region", { name: "Configure analysis", exact: true })).toBeVisible();
    const revokingRequest = await playwright.request.newContext({
      baseURL: E2E_API_ORIGIN,
      extraHTTPHeaders: { Origin: E2E_WEB_ORIGIN },
      storageState: await appApi.storageState(),
    });
    const response = await revokingRequest.post("/auth/logout", {
      headers: { "X-CSRF-Token": appApi.csrf },
    });
    expect(response.status()).toBe(204);
    await revokingRequest.dispose();

    let mutationRejected = false;
    try {
      await appApi.createHistoricalAnalysis({
        symbol: "BTCUSDT",
        presetCode: "price_sma_200_cross_above_1h",
        presetVersion: 1,
        analysisStart: "2026-07-20T00:00:00Z",
        analysisEnd: "2026-08-03T00:00:00Z",
      });
    } catch {
      mutationRejected = true;
    }
    expect(mutationRejected).toBe(true);
    await newAuthenticatedPage.reload();
    await expect(newAuthenticatedPage).toHaveURL(/\/sign-in/);
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  });

  test("revalidates the session on live-feed authentication expiry", async ({
    appApi,
    newAuthenticatedPage,
    playwright,
  }) => {
    await newAuthenticatedPage.goto("/preset-signals");
    const signals = new PresetSignalsPage(newAuthenticatedPage);
    await signals.openHistory();
    await expect(newAuthenticatedPage.getByText("Live updates connected.", { exact: true })).toBeVisible({ timeout: 30_000 });

    const revokingRequest = await playwright.request.newContext({
      baseURL: E2E_API_ORIGIN,
      extraHTTPHeaders: { Origin: E2E_WEB_ORIGIN },
      storageState: await appApi.storageState(),
    });
    const response = await revokingRequest.post("/auth/logout", {
      headers: { "X-CSRF-Token": appApi.csrf },
    });
    expect(response.status()).toBe(204);
    await revokingRequest.dispose();

    await expect
      .poll(() => newAuthenticatedPage.url(), {
        intervals: [1_000, 2_000, 5_000],
        timeout: 90_000,
      })
      .toMatch(/\/sign-in/);
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  });

  test("recovers a temporary Telegram failure without claiming delivery", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    const telegramPanel = connectedTelegramPage.locator("#telegram-connection");
    await providerSimulator.queueTelegramOutcomes(["temporary_failure", "sent"]);
    const telegram = new TelegramPage(connectedTelegramPage);
    await telegram.sendTest();
    await expect(telegramPanel.getByText("retrying", { exact: true })).toBeVisible();
    await expect
      .poll(async () => {
        const payload = await providerSimulator.getTelegramMessages();
        const messages = Array.isArray(payload.messages) ? payload.messages : [];
        return messages.some(
          (message) =>
            (message as { outcome?: string }).outcome === "sent",
        );
      })
      .toBe(true);
    await expect(telegramPanel.getByText("Telegram accepted the test notification.", { exact: true })).toBeVisible();
  });

  test("pauses an alert during Binance disconnect and resumes after reconnect", async ({
    appApi,
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await appApi.createPriceAlert({
      symbol: "BTCUSDT",
      direction: "cross_above",
      targetPrice: "101.000000",
    });
    await connectedTelegramPage.goto("/price-alerts");
    await expect(connectedTelegramPage.getByText(/BTCUSDT/).first()).toBeVisible();

    await providerSimulator.disconnectBinance();
    await connectedTelegramPage.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(connectedTelegramPage.getByText("The market-data connection is unavailable. Evaluation will resume after reconnecting.", { exact: true })).toBeVisible();

    await providerSimulator.reconnectBinance();
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
    await expect(connectedTelegramPage.getByText("The market-data connection is unavailable. Evaluation will resume after reconnecting.", { exact: true })).toBeHidden();
    expect(((await appApi.listAlerts()).alerts as unknown[])).toHaveLength(1);
  });

  test("keeps unavailable catalogue symbols out of new selections", async ({
    appApi,
    newAuthenticatedPage,
    providerSimulator,
  }) => {
    await providerSimulator.reset({ unavailableSymbols: ["SOLUSDT"] });
    await expect
      .poll(
        async () => {
          const response = await appApi.getMarkets();
          const markets = Array.isArray(response.markets)
            ? (response.markets as Array<{ symbol?: string; status?: string }>)
            : [];
          return markets.find((market) => market.symbol === "SOLUSDT")?.status;
        },
        { intervals: [1_000, 2_000, 5_000], timeout: 90_000 },
      )
      .toBe("unavailable");

    await newAuthenticatedPage.goto("/historical-analysis");
    await expect(newAuthenticatedPage.getByRole("region", { name: "Configure analysis", exact: true })).toBeVisible();
    await newAuthenticatedPage.locator("#historical-analysis-market").click();
    await expect(newAuthenticatedPage.getByRole("option", { name: /SOLUSDT/ })).toHaveCount(0);
  });

  test("replays missed SSE events, resets retained history, and applies invalidation once", async ({
    appApi,
    authenticatedSession,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const preset = {
      code: "price_sma_200_cross_above_1h",
      version: 1,
    };
    await appApi.subscribe({ symbol: "BTCUSDT", presetCode: preset.code, presetVersion: preset.version });
    await e2eControl.createSignalFeedFixture({
      userId: authenticatedSession.userId,
      symbol: "BTCUSDT",
      presetCode: preset.code,
      presetVersion: preset.version,
      count: 2,
    });

    const signals = new PresetSignalsPage(newAuthenticatedPage);
    await signals.goto();
    await signals.openHistory();
    await expect(newAuthenticatedPage.getByText("Live updates connected.", { exact: true })).toBeVisible();

    await newAuthenticatedPage.context().setOffline(true);
    await expect(newAuthenticatedPage.getByText("Live updates interrupted. Reconnecting…", { exact: true })).toBeVisible();
    await e2eControl.createSignalFeedFixture({
      userId: authenticatedSession.userId,
      symbol: "BTCUSDT",
      presetCode: preset.code,
      presetVersion: preset.version,
      count: 150,
      invalidatedCount: 0,
    });
    await newAuthenticatedPage.context().setOffline(false);
    await expect(newAuthenticatedPage.getByText("Live updates connected.", { exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Refresh", exact: true })).toBeVisible();

    await e2eControl.invalidateLatestSignal({
      userId: authenticatedSession.userId,
      symbol: "BTCUSDT",
      presetCode: preset.code,
      presetVersion: preset.version,
    });
    await expect(newAuthenticatedPage.getByText("Invalidated", { exact: true }).first()).toBeVisible();
    await expect(newAuthenticatedPage.getByText("Replayed after live-feed recovery", { exact: true })).toHaveCount(0);
    await expect(
      newAuthenticatedPage.getByRole("heading", {
        name: "Signal history",
        exact: true,
      }),
    ).toBeVisible();
  });
});
