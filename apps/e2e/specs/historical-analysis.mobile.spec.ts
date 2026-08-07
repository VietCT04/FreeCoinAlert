import { expect, test } from "../fixtures/test";
import { HISTORICAL_SCENARIOS } from "../fixtures/historical-scenarios";
import { expectNoPageOverflow, waitForHistoricalStatus } from "../support/historical-analysis";

test.describe.configure({ mode: "serial" });
test.setTimeout(120_000);

async function selectRun(page: import("@playwright/test").Page, symbol: string) {
  await page.getByRole("button", { name: "View analysis history", exact: true }).click();
  const sheet = page.getByRole("dialog", { name: "Analysis history", exact: true });
  await expect(sheet).toBeVisible();
  const run = sheet.getByRole("button").filter({ hasText: symbol }).first();
  await expect(run).toBeVisible();
  await run.click();
  await expect(page.getByText("Status", { exact: true })).toBeVisible();
}

test.describe("mobile historical analysis", () => {
  test.afterEach(async ({ e2eControl }) => {
    await e2eControl.reset();
  });

  test("configures a market and preset, reviews the UTC request, and returns safely", async ({
    newAuthenticatedPage,
  }) => {
    await newAuthenticatedPage.goto("/historical-analysis");
    await expect(newAuthenticatedPage.getByRole("region", { name: "Start an analysis", exact: true })).toBeVisible();
    await newAuthenticatedPage.locator("#historical-analysis-market").click();
    await newAuthenticatedPage.getByRole("option", { name: /BTCUSDT/ }).click();
    await newAuthenticatedPage.locator("#historical-analysis-preset").click();
    await newAuthenticatedPage.getByRole("option").first().click();
    await newAuthenticatedPage.getByRole("button", { name: "Review and run", exact: true }).click();
    const dialog = newAuthenticatedPage.getByRole("dialog", { name: "Review analysis" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("No live actions", { exact: true })).toBeVisible();
    await expect(dialog.getByText("Date range", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Back", exact: true }).click();
    await expect(dialog).toBeHidden();
    await expectNoPageOverflow(newAuthenticatedPage);
  });

  test("shows processing, opens cancellation, and preserves a cancelled result", async ({
    appApi,
    authenticatedSession,
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
    const runId = String(fixture.runId);
    await newAuthenticatedPage.goto("/historical-analysis");
    await selectRun(newAuthenticatedPage, scenario.symbol);
    await expect(newAuthenticatedPage.getByText("Queued.", { exact: true })).toBeVisible();
    await newAuthenticatedPage.getByRole("button", { name: "Cancel analysis", exact: true }).click();
    const dialog = newAuthenticatedPage.getByRole("alertdialog", { name: "Cancel this historical analysis?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Confirm cancellation", exact: true }).click();
    await expect(newAuthenticatedPage.getByText("No report was created for this cancelled analysis.", { exact: true })).toBeVisible();
    await expect((await waitForHistoricalStatus(appApi, runId, "cancelled")).run).toBeTruthy();
    await expectNoPageOverflow(newAuthenticatedPage);
  });

  test("opens previous analyses and keeps chart, table, tabs, and pagination usable", async ({
    authenticatedSession,
    e2eControl,
    newAuthenticatedPage,
    appApi,
  }) => {
    const scenario = HISTORICAL_SCENARIOS["analysis-paginated"];
    const fixture = await e2eControl.createHistoricalFixture({
      userId: authenticatedSession.userId,
      scenario: scenario.scenario,
      symbol: scenario.symbol,
      presetCode: scenario.presetCode,
      presetVersion: scenario.presetVersion,
      rangeDays: 90,
    });
    await waitForHistoricalStatus(appApi, String(fixture.runId), "succeeded");

    await newAuthenticatedPage.goto("/historical-analysis");
    await newAuthenticatedPage.getByRole("button", { name: "View analysis history", exact: true }).click();
    const sheet = newAuthenticatedPage.getByRole("dialog", { name: "Analysis history" });
    await expect(sheet).toBeVisible();
    await sheet.getByRole("button").filter({ hasText: scenario.symbol }).first().click();
    await expect(
      newAuthenticatedPage.getByRole("region", {
        name: "Historical hypothetical simulation",
        exact: true,
      }),
    ).toBeVisible();
    await newAuthenticatedPage.getByRole("tab", { name: "Hypothetical trades", exact: true }).click();
    await expect(
      newAuthenticatedPage.getByRole("table", { name: /Immutable hypothetical trades/ }),
    ).toBeVisible();
    const trades = newAuthenticatedPage.getByRole("button", { name: "Load more trades", exact: true });
    if (await trades.isVisible()) {
      await trades.click();
    }
    await newAuthenticatedPage.getByRole("tab", { name: "Equity data", exact: true }).click();
    await expect(
      newAuthenticatedPage.getByRole("table", { name: /Detailed immutable hypothetical equity points/ }),
    ).toBeVisible();
    const equity = newAuthenticatedPage.getByRole("button", { name: "Load more equity data", exact: true });
    if (await equity.isVisible()) {
      await equity.click();
    }
    await newAuthenticatedPage.getByRole("tab", { name: "Methodology", exact: true }).click();
    await newAuthenticatedPage.getByText("View dataset and result fingerprints", { exact: true }).click();
    await expect(newAuthenticatedPage.getByRole("button", { name: "Copy fingerprint", exact: true }).first()).toBeVisible();
    await expectNoPageOverflow(newAuthenticatedPage);
  });
});
