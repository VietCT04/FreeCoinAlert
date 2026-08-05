import { PresetSignalsPage } from "../pages/preset-signals.page";
import { expect, test } from "../fixtures/test";

test.describe.configure({ mode: "serial" });

test.describe("preset signals and browser history", () => {
  test("filters the catalog, exposes fixed technical details, and manages a subscription lifecycle", async ({
    newAuthenticatedPage,
  }) => {
    const presets = new PresetSignalsPage(newAuthenticatedPage);
    await presets.goto();
    await presets.chooseMarket("BTCUSDT");
    await presets.chooseTimeframe("1 hour");
    await presets.chooseSubscription("Not subscribed");

    await expect(newAuthenticatedPage.getByRole("heading", { name: "1 hour presets", exact: true })).toBeVisible();
    await newAuthenticatedPage.getByText("Technical details", { exact: true }).first().click();
    for (const label of [
      "Preset code/version",
      "Strategy type",
      "Timeframe",
      "Direction",
      "Period",
      "Threshold",
      "Close-price input",
      "Definition",
    ]) {
      await expect(newAuthenticatedPage.getByText(label, { exact: true }).first()).toBeVisible();
    }

    await newAuthenticatedPage.getByRole("button", { name: "Subscribe", exact: true }).first().click();
    await presets.chooseSubscription("Subscribed");
    await expect(newAuthenticatedPage.getByText("Subscribed", { exact: true }).first()).toBeVisible();
    await newAuthenticatedPage.getByRole("button", { name: "Disable", exact: true }).first().click();
    await expect(newAuthenticatedPage.getByRole("alertdialog", { name: "Disable this signal subscription?" })).toBeVisible();
    await newAuthenticatedPage.getByRole("alertdialog").getByRole("button", { name: "Disable signal", exact: true }).click();
    await presets.chooseSubscription("Not subscribed");
    await expect(newAuthenticatedPage.getByText("Disabled", { exact: true }).first()).toBeVisible();
    await newAuthenticatedPage.getByRole("button", { name: "Subscribe", exact: true }).first().click();
    await presets.chooseSubscription("Subscribed");
    await expect(newAuthenticatedPage.getByText("Subscribed", { exact: true }).first()).toBeVisible();
  });

  test("confirms Telegram delivery readiness and keeps website history separate", async ({
    connectedTelegramPage,
  }) => {
    const presets = new PresetSignalsPage(connectedTelegramPage);
    await presets.goto();
    await presets.chooseMarket("BTCUSDT");
    await connectedTelegramPage.getByRole("button", { name: "Subscribe", exact: true }).first().click();
    await expect(connectedTelegramPage.getByRole("heading", { name: "Telegram delivery", exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByText("Ready", { exact: true }).last()).toBeVisible();

    const deliverySwitch = connectedTelegramPage.getByRole("switch", { name: "Delivery preference", exact: true }).first();
    await deliverySwitch.click();
    await expect(connectedTelegramPage.getByRole("alertdialog", { name: "Enable Telegram delivery?" })).toBeVisible();
    await connectedTelegramPage.getByRole("alertdialog").getByRole("button", { name: "Enable Telegram", exact: true }).click();
    await expect(connectedTelegramPage.getByText("On", { exact: true }).first()).toBeVisible();

    await deliverySwitch.click();
    await expect(connectedTelegramPage.getByText("Off", { exact: true }).first()).toBeVisible();
    await presets.openHistory();
    await expect(connectedTelegramPage.getByRole("heading", { name: "Signal history", exact: true })).toBeVisible();
  });

  test("paginates owner-visible history, filters it, and handles sound activation and mute", async ({
    appApi,
    authenticatedSession,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const presetsResponse = (await appApi.getPresets()) as {
      presets: Array<{ code: string; version: number }>;
    };
    const preset = presetsResponse.presets[0];
    if (!preset) {
      throw new Error("The seeded E2E signal preset is unavailable.");
    }
    await appApi.subscribe({
      symbol: "BTCUSDT",
      presetCode: preset.code,
      presetVersion: preset.version,
    });
    await e2eControl.createSignalFeedFixture({
      userId: authenticatedSession.userId,
      symbol: "BTCUSDT",
      presetCode: preset.code,
      presetVersion: preset.version,
      count: 100,
      invalidatedCount: 1,
    });

    const page = new PresetSignalsPage(newAuthenticatedPage);
    await page.goto();
    await page.openHistory();
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Signal history", exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByText("Current", { exact: true }).first()).toBeVisible();
    await expect(newAuthenticatedPage.getByText("Invalidated", { exact: true }).first()).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Load more", exact: true })).toBeVisible();

    await newAuthenticatedPage.locator("#signal-feed-market-filter").click();
    await newAuthenticatedPage.getByRole("option", { name: /BTCUSDT/ }).click();
    await newAuthenticatedPage.locator("#signal-feed-preset-filter").click();
    await newAuthenticatedPage.getByRole("option", { name: /·/ }).last().click();
    await newAuthenticatedPage.getByRole("button", { name: "Load more", exact: true }).click();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Load more", exact: true })).toBeHidden();

    await newAuthenticatedPage.getByRole("tab", { name: "Presets", exact: true }).click();
    await newAuthenticatedPage.getByRole("button", { name: "View history", exact: true }).first().click();
    await expect(newAuthenticatedPage.getByRole("tab", { name: "Signal history", exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Signal history", exact: true })).toBeFocused();

    const enableSound = newAuthenticatedPage.getByRole("button", { name: "Enable sound", exact: true });
    if (await enableSound.isVisible()) {
      await enableSound.click();
    }
    const muteSound = newAuthenticatedPage.getByRole("button", { name: "Mute sound", exact: true });
    if (await muteSound.isVisible()) {
      await muteSound.click();
      await expect(newAuthenticatedPage.getByRole("button", { name: "Enable sound", exact: true })).toBeVisible();
    }
  });

  test("receives a deterministic live event and one Telegram delivery without duplicate entries", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    const page = new PresetSignalsPage(connectedTelegramPage);
    await page.goto();
    await page.chooseMarket("ETHUSDT");
    await connectedTelegramPage.getByRole("button", { name: "Subscribe", exact: true }).first().click();
    const deliverySwitch = connectedTelegramPage.getByRole("switch", { name: "Delivery preference", exact: true }).first();
    await deliverySwitch.click();
    await connectedTelegramPage.getByRole("alertdialog").getByRole("button", { name: "Enable Telegram", exact: true }).click();
    await page.openHistory();
    await expect(connectedTelegramPage.getByText(/Live|Connecting/).first()).toBeVisible();
    await providerSimulator.publishClosedKlineRange({
      symbol: "ETHUSDT",
      startTimeMs: Date.parse(process.env.E2E_CLOCK_NOW ?? "2026-08-04T00:00:00.000Z"),
      count: 60,
      openPrice: "100",
      closePrice: "100",
      highPrice: "100",
      lowPrice: "100",
    });
    await providerSimulator.publishClosedKlineRange({
      symbol: "ETHUSDT",
      startTimeMs: Date.parse(process.env.E2E_CLOCK_NOW ?? "2026-08-04T00:00:00.000Z") + 60 * 60_000,
      count: 60,
      openPrice: "500",
      closePrice: "500",
      highPrice: "500",
      lowPrice: "500",
    });
    await expect(connectedTelegramPage.getByText("New live signal", { exact: true }).first()).toBeVisible();
    await expect(connectedTelegramPage.getByText("New live signal", { exact: true })).toHaveCount(1);
    await expect
      .poll(async () => {
        const state = await providerSimulator.getTelegramMessages();
        const messages = Array.isArray(state.messages) ? state.messages : [];
        return messages.filter((message) => (message as { outcome?: string }).outcome === "sent").length;
      })
      .toBe(1);
  });
});
