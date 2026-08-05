import { expect, test } from "../fixtures/test";
import { PresetSignalsPage } from "../pages/preset-signals.page";
import { PriceAlertsPage } from "../pages/price-alerts.page";
import { TelegramPage } from "../pages/telegram.page";
import { expectNoPageOverflow } from "../support/historical-analysis";

test.describe.configure({ mode: "serial" });

test.describe("mobile authenticated workflows", () => {
  test("covers sign-in and the dashboard drawer without page overflow", async ({
    newAnonymousPage,
    newAuthenticatedPage,
  }) => {
    await newAnonymousPage.goto("/sign-in");
    await expect(newAnonymousPage.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
    await expectNoPageOverflow(newAnonymousPage);

    await newAuthenticatedPage.goto("/dashboard");
    const trigger = newAuthenticatedPage.getByRole("button", { name: "Open navigation", exact: true });
    await trigger.click();
    const drawer = newAuthenticatedPage.getByRole("dialog", { name: "Sidebar", exact: true });
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole("link", { name: "Price Alerts", exact: true })).toBeVisible();
    await newAuthenticatedPage.keyboard.press("Escape");
    await expect(trigger).toBeFocused();
    await expectNoPageOverflow(newAuthenticatedPage);
  });

  test("filters and creates a one-time price alert from the mobile dialog", async ({
    connectedTelegramPage,
  }) => {
    const alerts = new PriceAlertsPage(connectedTelegramPage);
    await alerts.goto();
    await alerts.selectStatus("Active");
    await alerts.selectStatus("All");
    await alerts.openCreate();
    await expect(connectedTelegramPage.getByRole("dialog", { name: "Create price alert" })).toBeVisible();
    await alerts.chooseMarket("BTCUSDT");
    await alerts.chooseCondition("Crosses above");
    await alerts.fillTarget("101.000000");
    await alerts.submitCreate();
    await expect(connectedTelegramPage.getByRole("dialog", { name: "Create price alert" })).toBeHidden();
    await expect(connectedTelegramPage.getByText("BTCUSDT", { exact: true }).first()).toBeVisible();
    await expectNoPageOverflow(connectedTelegramPage);
  });

  test("filters presets, opens details, changes tabs, and handles confirmation dialogs", async ({
    connectedTelegramPage,
  }) => {
    const presets = new PresetSignalsPage(connectedTelegramPage);
    await presets.goto();
    await presets.chooseMarket("BTCUSDT");
    await presets.chooseTimeframe("1 hour");
    await presets.chooseSubscription("Not subscribed");
    await connectedTelegramPage.getByText("Technical details", { exact: true }).first().click();
    await expect(connectedTelegramPage.getByText("Preset code/version", { exact: true }).first()).toBeVisible();
    await connectedTelegramPage.getByRole("button", { name: "Subscribe", exact: true }).first().click();
    await expect(connectedTelegramPage.getByRole("heading", { name: "Telegram delivery", exact: true })).toBeVisible();
    const deliverySwitch = connectedTelegramPage.getByRole("switch", { name: "Delivery preference", exact: true }).first();
    await deliverySwitch.click();
    await expect(connectedTelegramPage.getByRole("alertdialog", { name: "Enable Telegram delivery?" })).toBeVisible();
    await connectedTelegramPage.keyboard.press("Escape");
    await expect(connectedTelegramPage.getByRole("alertdialog", { name: "Enable Telegram delivery?" })).toBeHidden();
    await presets.openHistory();
    await expect(connectedTelegramPage.getByRole("heading", { name: "Signal history", exact: true })).toBeVisible();
    await expectNoPageOverflow(connectedTelegramPage);
  });

  test("links Telegram from the mobile connection card", async ({
    newAuthenticatedPage,
  }) => {
    const telegram = new TelegramPage(newAuthenticatedPage);
    const popup = await telegram.createLink();
    await expect(popup.getByText("E2E Telegram simulator", { exact: true })).toBeVisible();
    await popup.close();
    await expect(newAuthenticatedPage.getByText("Linking", { exact: true })).toBeVisible();
    await expectNoPageOverflow(newAuthenticatedPage);
  });

  test("sends a Telegram test notification and disconnects safely", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await providerSimulator.queueTelegramOutcomes(["sent"]);
    const connectedTelegram = new TelegramPage(connectedTelegramPage);
    await connectedTelegram.sendTest();
    await expect(connectedTelegramPage.getByText("Telegram accepted the test notification.", { exact: true })).toBeVisible();
    await connectedTelegram.confirmDisconnect();
    await expect(connectedTelegramPage.getByText("Disconnected", { exact: true })).toBeVisible();
    await expectNoPageOverflow(connectedTelegramPage);
  });
});
