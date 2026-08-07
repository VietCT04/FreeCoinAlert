import type { Page } from "@playwright/test";

import { expect, test } from "../fixtures/test";
import { HISTORICAL_SCENARIOS } from "../fixtures/historical-scenarios";
import {
  seriousAccessibilityViolations,
  type AccessibilityResult,
} from "../support/accessibility";
import { waitForHistoricalStatus } from "../support/historical-analysis";

test.describe.configure({ mode: "serial" });
test.setTimeout(120_000);

async function expectStableAccessibility(
  checkAccessibility: (
    label: string,
    targetPage?: Page,
  ) => Promise<AccessibilityResult>,
  page: Page,
  label: string,
) {
  const result = await checkAccessibility(label, page);
  expect(seriousAccessibilityViolations(result)).toEqual([]);
}

test.describe("stable browser accessibility states", () => {
  test("scans sign-in and sign-up forms", async ({ checkAccessibility, newAnonymousPage }) => {
    await newAnonymousPage.goto("/sign-in");
    await expect(newAnonymousPage.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAnonymousPage, "sign-in");

    await newAnonymousPage.goto("/sign-up");
    await expect(newAnonymousPage.getByRole("heading", { name: "Create an account", exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAnonymousPage, "sign-up");
  });

  test("scans an empty dashboard state", async ({ checkAccessibility, newAuthenticatedPage }) => {
    await newAuthenticatedPage.goto("/dashboard");
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("heading", { name: "No recent activity", exact: true })).toBeVisible();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Refresh", exact: true })).toBeEnabled();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "dashboard-empty");
  });

  test("scans a populated authenticated dashboard state", async ({ checkAccessibility, connectedTelegramPage }) => {
    await connectedTelegramPage.goto("/dashboard");
    await expect(connectedTelegramPage.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, connectedTelegramPage, "dashboard-populated");
  });

  test("scans price-alert list and create dialog", async ({ checkAccessibility, connectedTelegramPage }) => {
    await connectedTelegramPage.goto("/price-alerts");
    await expect(connectedTelegramPage.getByRole("heading", { name: "Price Alerts", exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, connectedTelegramPage, "price-alerts-list");
    await connectedTelegramPage.getByRole("button", { name: "Create alert", exact: true }).click();
    await expect(connectedTelegramPage.getByRole("dialog", { name: "Create price alert" })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, connectedTelegramPage, "price-alerts-dialog");
    await connectedTelegramPage.getByRole("dialog").getByRole("button", { name: "Cancel", exact: true }).click();
  });

  test("scans preset catalogue and signal history", async ({ checkAccessibility, newAuthenticatedPage }) => {
    await newAuthenticatedPage.goto("/preset-signals");
    await expect(newAuthenticatedPage.getByRole("heading", { name: /presets/i }).first()).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "preset-catalogue");
    await newAuthenticatedPage.getByRole("tab", { name: "Signal history", exact: true }).click();
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Signal history", exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "preset-history");
  });

  test("scans a disconnected Telegram state", async ({ checkAccessibility, newAuthenticatedPage }) => {
    await newAuthenticatedPage.goto("/telegram");
    await expect(newAuthenticatedPage.getByText("Not connected", { exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "telegram-disconnected");
  });

  test("scans a connected Telegram state", async ({ checkAccessibility, connectedTelegramPage }) => {
    await connectedTelegramPage.goto("/telegram");
    await expect(connectedTelegramPage.getByText("Connected", { exact: true }).first()).toBeVisible();
    await expectStableAccessibility(checkAccessibility, connectedTelegramPage, "telegram-connected");
  });

  test("scans historical configure and review dialog states", async ({ checkAccessibility, newAuthenticatedPage }) => {
    await newAuthenticatedPage.goto("/historical-analysis");
    await expect(newAuthenticatedPage.getByRole("region", { name: "Start an analysis", exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-configure");
    await newAuthenticatedPage.getByRole("button", { name: "Review and run", exact: true }).click();
    await expect(newAuthenticatedPage.getByRole("dialog", { name: "Review analysis" })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-review");
  });

  test("scans historical processing and success report states", async ({
    appApi,
    authenticatedSession,
    checkAccessibility,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const scenario = HISTORICAL_SCENARIOS["analysis-positive"];
    await e2eControl.gateHistoricalWorkerBeforeClaim();
    const fixture = await e2eControl.createHistoricalFixture({
      userId: authenticatedSession.userId,
      scenario: scenario.scenario,
      symbol: scenario.symbol,
      presetCode: scenario.presetCode,
      presetVersion: scenario.presetVersion,
    });
    await newAuthenticatedPage.goto("/historical-analysis");
    await expect(newAuthenticatedPage.getByRole("button").filter({ hasText: scenario.symbol }).first()).toBeVisible();
    await newAuthenticatedPage.getByRole("button").filter({ hasText: scenario.symbol }).first().click();
    await expect(newAuthenticatedPage.getByText("Queued.", { exact: true })).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-processing");
    await e2eControl.releaseHistoricalWorkerBeforeClaim();
    await waitForHistoricalStatus(appApi, String(fixture.runId), "succeeded");
    await newAuthenticatedPage.reload();
    const completedRun = newAuthenticatedPage
      .getByRole("button")
      .filter({ hasText: scenario.symbol })
      .first();
    await expect(completedRun).toBeVisible();
    await completedRun.click();
    await expect(
      newAuthenticatedPage.getByRole("tab", { name: "Methodology", exact: true }),
    ).toBeVisible();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-success");
    await newAuthenticatedPage.getByRole("tab", { name: "Methodology", exact: true }).click();
    await newAuthenticatedPage.getByText("View dataset and result fingerprints", { exact: true }).click();
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-methodology");
  });

  test("scans the zero-trade report and its explicit undefined metrics", async ({
    appApi,
    authenticatedSession,
    checkAccessibility,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const scenario = HISTORICAL_SCENARIOS["analysis-zero-trade"];
    const fixture = await e2eControl.createHistoricalFixture({
      userId: authenticatedSession.userId,
      scenario: scenario.scenario,
      symbol: scenario.symbol,
      presetCode: scenario.presetCode,
      presetVersion: scenario.presetVersion,
    });
    await waitForHistoricalStatus(appApi, String(fixture.runId), "succeeded");
    await newAuthenticatedPage.goto("/historical-analysis");
    await newAuthenticatedPage.getByRole("button").filter({ hasText: scenario.symbol }).first().click();
    await expect(
      newAuthenticatedPage.getByRole("region", {
        name: "Historical hypothetical simulation",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      newAuthenticatedPage.getByText(/Not defined .* no completed trades\./),
    ).toHaveCount(2);
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-zero-trade");
  });

  test("keeps dialog focus, keyboard tabs, labels, and reduced motion stable", async ({
    checkAccessibility,
    newAuthenticatedPage,
  }) => {
    await newAuthenticatedPage.emulateMedia({ reducedMotion: "reduce" });
    await newAuthenticatedPage.goto("/historical-analysis");
    const review = newAuthenticatedPage.getByRole("button", { name: "Review and run", exact: true });
    await review.focus();
    await expect(review).toBeFocused();
    await review.click();
    const dialog = newAuthenticatedPage.getByRole("dialog", { name: "Review analysis" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Back", exact: true })).toBeVisible();
    const dialogHasFocus = await dialog.evaluate((element) => element.contains(document.activeElement));
    expect(dialogHasFocus).toBe(true);
    await newAuthenticatedPage.keyboard.press("Tab");
    const focusRemainsInDialog = await dialog.evaluate((element) => element.contains(document.activeElement));
    expect(focusRemainsInDialog).toBe(true);
    await expectStableAccessibility(checkAccessibility, newAuthenticatedPage, "historical-review-reduced-motion");
  });
});
