import { TelegramPage } from "../pages/telegram.page";
import { expect, test } from "../fixtures/test";

test.describe.configure({ mode: "serial" });

test.describe("Telegram connection and delivery", () => {
  test("shows the disconnected readiness state and prevents test delivery", async ({
    newAuthenticatedPage,
  }) => {
    const telegram = new TelegramPage(newAuthenticatedPage);
    await telegram.goto();

    await expect(newAuthenticatedPage.getByText("Not connected", { exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Connect Telegram", exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Send test notification", exact: true })).toBeHidden();
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Notification usage", exact: true })).toBeVisible();
  });

  test("exposes linking state and handles an expired generated link", async ({
    appApi,
    e2eControl,
    newAuthenticatedPage,
    authenticatedSession,
  }) => {
    const telegram = new TelegramPage(newAuthenticatedPage);
    await appApi.createTelegramLink();
    await telegram.goto();
    await expect(newAuthenticatedPage.getByText("Linking", { exact: true })).toBeVisible();
    await e2eControl.expireTelegramLink(authenticatedSession.userId);
    await telegram.refresh();
    await expect(newAuthenticatedPage.getByText("Not connected", { exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Connect Telegram", exact: true })).toBeVisible();
  });

  test("connects through the real poller, refreshes status, and confirms disconnect", async ({
    connectedTelegramPage,
  }) => {
    const telegram = new TelegramPage(connectedTelegramPage);
    await expect(connectedTelegramPage.getByText("Connected", { exact: true })).toBeVisible();
    await telegram.refresh();
    await expect(connectedTelegramPage.getByText("Connected", { exact: true })).toBeVisible();

    await telegram.confirmDisconnect();
    await expect(connectedTelegramPage.getByText("Disconnected", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByRole("button", { name: "Connect Telegram", exact: true })).toBeVisible();
  });

  test("renders a successful provider-accepted test notification", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await providerSimulator.queueTelegramOutcomes(["sent"]);
    await connectedTelegramPage.getByRole("button", { name: "Send test notification", exact: true }).click();
    await expect(connectedTelegramPage.getByText("Telegram accepted the test notification.", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByText("sent", { exact: true })).toBeVisible();
  });

  test("exposes temporary and rate-limited provider outcomes as pending retry states", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await providerSimulator.queueTelegramOutcomes(["temporary_failure", "rate_limited"]);
    await connectedTelegramPage.getByRole("button", { name: "Send test notification", exact: true }).click();
    await expect(connectedTelegramPage.getByText("retrying", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByText("Telegram asked us to retry. The notification is still pending.", { exact: true })).toBeVisible();
  });

  test("keeps permanent and uncertain provider outcomes distinct", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await providerSimulator.queueTelegramOutcomes(["permanent_failure"]);
    await connectedTelegramPage.getByRole("button", { name: "Send test notification", exact: true }).click();
    await expect(connectedTelegramPage.getByText("failed", { exact: true })).toBeVisible();
    await expect(connectedTelegramPage.getByText("The test notification could not be sent.", { exact: true })).toBeVisible();
  });

  test("surfaces an uncertain provider result without claiming delivery", async ({
    connectedTelegramPage,
    providerSimulator,
  }) => {
    await providerSimulator.queueTelegramOutcomes(["uncertain"]);
    await connectedTelegramPage.getByRole("button", { name: "Send test notification", exact: true }).click();
    await expect(connectedTelegramPage.getByText("We could not confirm whether Telegram accepted the message. Check Telegram before trying again.", { exact: true })).toBeVisible();
  });
});
