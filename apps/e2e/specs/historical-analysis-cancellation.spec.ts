import { expect, test } from "../fixtures/test";
import { HISTORICAL_SCENARIOS } from "../fixtures/historical-scenarios";
import { waitForHistoricalStatus } from "../support/historical-analysis";

test.describe.configure({ mode: "serial" });
test.setTimeout(120_000);

async function selectRun(page: import("@playwright/test").Page, symbol: string) {
  const run = page.getByRole("button").filter({ hasText: symbol }).first();
  await expect(run).toBeVisible();
  await run.click();
  await expect(page.getByText("Run status", { exact: true })).toBeVisible();
}

test.describe("historical analysis cancellation checkpoints", () => {
  test.afterEach(async ({ e2eControl }) => {
    await e2eControl.reset();
  });

  test("cancels a queued run before claim and creates no report", async ({
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
    expect(((await appApi.getHistoricalAnalysis(runId)).run as { status: string }).status).toBe("queued");

    await newAuthenticatedPage.goto("/historical-analysis");
    await selectRun(newAuthenticatedPage, scenario.symbol);
    await newAuthenticatedPage.getByRole("button", { name: "Cancel analysis", exact: true }).click();
    const dialog = newAuthenticatedPage.getByRole("alertdialog", { name: "Cancel this historical analysis?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Confirm cancellation", exact: true }).click();
    await expect(newAuthenticatedPage.getByText("No report was created for this cancelled analysis.", { exact: true })).toBeVisible();

    const cancelled = await waitForHistoricalStatus(appApi, runId, "cancelled");
    expect((cancelled.run as { status: string }).status).toBe("cancelled");
    const replay = await appApi.cancelHistoricalAnalysis(runId);
    expect((replay.run as { status: string }).status).toBe("cancelled");
    await e2eControl.releaseHistoricalWorkerBeforeClaim();
  });

  test("cancels a running run after claim and stops at a safe checkpoint", async ({
    appApi,
    authenticatedSession,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const scenario = HISTORICAL_SCENARIOS["analysis-positive"];
    await e2eControl.gateHistoricalWorkerAfterClaim();
    const fixture = await e2eControl.createHistoricalFixture({
      userId: authenticatedSession.userId,
      scenario: scenario.scenario,
      symbol: scenario.symbol,
      presetCode: scenario.presetCode,
      presetVersion: scenario.presetVersion,
    });
    const runId = String(fixture.runId);
    await waitForHistoricalStatus(appApi, runId, "running");

    await newAuthenticatedPage.goto("/historical-analysis");
    await newAuthenticatedPage.reload();
    await selectRun(newAuthenticatedPage, scenario.symbol);
    await expect(newAuthenticatedPage.getByText("The analysis is running in the bounded worker.", { exact: true })).toBeVisible();
    await newAuthenticatedPage.getByRole("button", { name: "Cancel analysis", exact: true }).click();
    const dialog = newAuthenticatedPage.getByRole("alertdialog", { name: "Cancel this historical analysis?" });
    await dialog.getByRole("button", { name: "Confirm cancellation", exact: true }).click();
    await e2eControl.releaseHistoricalWorkerAfterClaim();

    await waitForHistoricalStatus(appApi, runId, "cancelled");
    await expect(newAuthenticatedPage.getByText("No report was created for this cancelled analysis.", { exact: true })).toBeVisible();
  });
});
