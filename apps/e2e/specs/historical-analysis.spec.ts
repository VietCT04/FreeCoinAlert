import { expect, test } from "../fixtures/test";
import {
  HISTORICAL_SCENARIOS,
  type HistoricalScenarioName,
} from "../fixtures/historical-scenarios";
import { waitForHistoricalStatus } from "../support/historical-analysis";

test.describe.configure({ mode: "serial" });
test.setTimeout(120_000);

function normalizeUtc(value: string): string {
  return value.replace("+00:00", "Z");
}

function utcDateOffset(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

async function selectScenarioRun(page: import("@playwright/test").Page, symbol: string) {
  const run = page.getByRole("button").filter({ hasText: symbol }).first();
  await expect(run).toBeVisible();
  await run.click();
  await expect(page.getByText("Status", { exact: true })).toBeVisible();
}

async function createScenario(
  e2eControl: import("../support/e2e-control").E2EControl,
  userId: string,
  scenario: HistoricalScenarioName,
) {
  const manifest = HISTORICAL_SCENARIOS[scenario];
  return e2eControl.createHistoricalFixture({
    userId,
    scenario,
    symbol: manifest.symbol,
    presetCode: manifest.presetCode,
    presetVersion: manifest.presetVersion,
    rangeDays: scenario === "analysis-paginated" ? 90 : 14,
  });
}

test.describe("historical analysis configuration and reports", () => {
  test.afterEach(async ({ e2eControl }) => {
    await e2eControl.reset();
  });

  test("validates UTC configuration, confirms the request, reloads, and preserves idempotency", async ({
    appApi,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    await e2eControl.gateHistoricalWorkerBeforeClaim();
    await newAuthenticatedPage.goto("/historical-analysis");
    await expect(
      newAuthenticatedPage.getByRole("region", { name: "Start an analysis", exact: true }),
    ).toBeVisible();
    await newAuthenticatedPage
      .getByRole("button", { name: "More information about historical analysis", exact: true })
      .click();
    const infoDialog = newAuthenticatedPage.getByRole("dialog", { name: "About this analysis" });
    await expect(infoDialog.getByText("Signals use confirmed candle closes.", { exact: true })).toBeVisible();
    await infoDialog.getByRole("button", { name: "Close", exact: true }).click();
    const configuration = await appApi.getHistoricalConfiguration();
    expect(configuration.minimumRangeDays).toBe(7);
    expect(configuration.maximumRangeDays).toBe(90);
    expect(configuration.maximumActiveRuns).toBe(2);
    const serverAssumptions = configuration.assumptions as Record<string, unknown>;
    expect(serverAssumptions.signalTiming).toBe("confirmed_candle_close");
    expect(serverAssumptions.entryTiming).toBe("next_candle_open");
    expect(serverAssumptions.holdingPeriodCandles).toBe(6);

    await newAuthenticatedPage.locator("#historical-analysis-market").click();
    await newAuthenticatedPage.getByRole("option", { name: /BTCUSDT/ }).click();
    await newAuthenticatedPage.locator("#historical-analysis-preset").click();
    await newAuthenticatedPage.getByRole("option").first().click();

    const start = newAuthenticatedPage.locator("#historical-analysis-start");
    const end = newAuthenticatedPage.locator("#historical-analysis-end");
    const review = newAuthenticatedPage.getByRole("button", { name: "Review and run", exact: true });

    await start.fill("2026-07-20");
    await end.fill("2026-07-20");
    await review.click();
    await expect(newAuthenticatedPage.getByText("Choose at least 7 complete UTC days.", { exact: true })).toBeVisible();

    await start.fill("2026-07-01");
    await end.fill(utcDateOffset(1));
    await review.click();
    await expect(newAuthenticatedPage.getByText("The UTC end date must be a completed day", { exact: false })).toBeVisible();

    await start.fill("2026-07-29");
    await end.fill("2026-08-02");
    await review.click();
    await expect(newAuthenticatedPage.getByText("Choose at least", { exact: false })).toBeVisible();

    await start.fill("2026-04-01");
    await end.fill("2026-08-02");
    await review.click();
    await expect(newAuthenticatedPage.getByText("Choose no more than", { exact: false })).toBeVisible();

    await start.fill("2026-07-20");
    await end.fill("2026-08-02");
    await review.click();
    const dialog = newAuthenticatedPage.getByRole("dialog", { name: "Review analysis" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("No live actions", { exact: true })).toBeVisible();
    await expect(dialog.getByText("2026-07-20 to 2026-08-02 (UTC)", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Back", exact: true }).click();
    await review.click();
    await dialog.getByRole("button", { name: "Start analysis", exact: true }).click();

    await expect(newAuthenticatedPage.getByText("Queued.", { exact: true })).toBeVisible();
    const listResponse = await appApi.listHistoricalAnalyses();
    const firstRun = (listResponse.runs as Array<{ id: string }> | undefined)?.[0];
    if (!firstRun) {
      throw new Error("The browser-created historical analysis was not listed.");
    }

    await newAuthenticatedPage.reload();
    await selectScenarioRun(newAuthenticatedPage, "BTCUSDT");
    await e2eControl.releaseHistoricalWorkerBeforeClaim();
    await waitForHistoricalStatus(appApi, firstRun.id, "succeeded");

    const idempotencyKey = "8b4c4f7e-6a63-4f31-9f64-e2d2d6f80a52";
    const first = await appApi.createHistoricalAnalysis({
      symbol: "BTCUSDT",
      presetCode: "price_sma_200_cross_above_1h",
      presetVersion: 1,
      analysisStart: "2026-07-20T00:00:00Z",
      analysisEnd: "2026-08-03T00:00:00Z",
      idempotencyKey,
    });
    const replay = await appApi.createHistoricalAnalysis({
      symbol: "BTCUSDT",
      presetCode: "price_sma_200_cross_above_1h",
      presetVersion: 1,
      analysisStart: "2026-07-20T00:00:00Z",
      analysisEnd: "2026-08-03T00:00:00Z",
      idempotencyKey,
    });
    expect((replay.run as { id: string }).id).toBe((first.run as { id: string }).id);
    await appApi.signOut();
    await newAuthenticatedPage.reload();
    await expect(newAuthenticatedPage).toHaveURL(/\/sign-in/);
  });

  for (const scenario of [
    "analysis-positive",
    "analysis-negative",
    "analysis-zero-trade",
  ] as const) {
    test(`${scenario} renders server-provided report context and metrics`, async ({
      appApi,
      authenticatedSession,
      e2eControl,
      newAuthenticatedPage,
    }) => {
      const manifest = HISTORICAL_SCENARIOS[scenario];
      const fixture = await createScenario(e2eControl, authenticatedSession.userId, scenario);
      const runId = String(fixture.runId);
      const runResponse = await waitForHistoricalStatus(appApi, runId, "succeeded");
      const reportResponse = await appApi.getHistoricalReport(runId);
      const report = reportResponse.report as {
        analysisStart: string;
        analysisEnd: string;
        datasetFingerprint: string;
        resultFingerprint: string;
        coverage: Record<string, unknown>;
        assumptions: Record<string, unknown>;
        safetyDisclosures: string[];
        summary: Record<string, string | number | null>;
        candlePreview: Array<Record<string, string | number>>;
        tradeMarkers: Array<Record<string, string | number>>;
      };

      expect((runResponse.run as { status: string }).status).toBe("succeeded");
      expect(normalizeUtc(report.analysisStart)).toBe(manifest.analysisStart);
      expect(normalizeUtc(report.analysisEnd)).toBe(manifest.analysisEnd);
      expect(normalizeUtc(String(report.coverage.analysisStart))).toBe(
        manifest.analysisStart,
      );
      expect(normalizeUtc(String(report.coverage.analysisEnd))).toBe(
        manifest.analysisEnd,
      );
      expect(report.summary.initialEquity).toBe(manifest.expected.initialEquity);
      expectMetricCount(
        report.summary.tradeCount,
        manifest.expected.tradeCount,
      );
      expectMetricCount(
        report.summary.winningTradeCount,
        manifest.expected.winningTradeCount,
      );
      expectMetricCount(
        report.summary.losingTradeCount,
        manifest.expected.losingTradeCount,
      );
      expectMetricSign(report.summary.netReturn, manifest.expected.netReturn);
      expectDrawdownSign(
        report.summary.maximumDrawdown,
        manifest.expected.maximumDrawdown,
      );
      if (manifest.expected.winRate === "defined") {
        expect(report.summary.winRate).not.toBeNull();
        expect(report.summary.winRateUndefinedReason).toBeNull();
      } else {
        expect(report.summary.winRate).toBeNull();
        expect(report.summary.winRateUndefinedReason).toBe(
          manifest.expected.undefinedReason,
        );
      }
      if (manifest.expected.profitFactor === "defined") {
        expect(report.summary.profitFactor).not.toBeNull();
        expect(report.summary.profitFactorUndefinedReason).toBeNull();
      } else {
        expect(report.summary.profitFactor).toBeNull();
        expect(report.summary.profitFactorUndefinedReason).toBe(
          manifest.expected.undefinedReason,
        );
      }
      expect(report.datasetFingerprint).toMatch(/^[a-f0-9]{64}$/);
      expect(report.resultFingerprint).toMatch(/^[a-f0-9]{64}$/);
      expect(report.assumptions.signalTiming).toBe("confirmed_candle_close");
      expect(report.assumptions.entryTiming).toBe("next_candle_open");
      expect(report.safetyDisclosures.length).toBeGreaterThan(0);
      expect(report.candlePreview.length).toBeGreaterThan(0);
      expect(report.candlePreview.length).toBeLessThanOrEqual(2500);
      expect(report.candlePreview[0].openPrice).toEqual(expect.any(String));
      expect(report.candlePreview[0].highPrice).toEqual(expect.any(String));
      expect(report.candlePreview[0].lowPrice).toEqual(expect.any(String));
      expect(report.candlePreview[0].closePrice).toEqual(expect.any(String));
      expect(report.tradeMarkers.length).toBeLessThanOrEqual(200);
      if (Number(report.summary.tradeCount) > 0) {
        expect(report.tradeMarkers.length).toBeGreaterThan(0);
      }

      await newAuthenticatedPage.goto("/historical-analysis");
      await expect(newAuthenticatedPage.getByRole("region", { name: "Start an analysis", exact: true })).toBeVisible();
      await selectScenarioRun(newAuthenticatedPage, manifest.symbol);
      await expect(
        newAuthenticatedPage.getByRole("region", {
          name: "Historical hypothetical simulation",
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        newAuthenticatedPage.getByRole("tab", {
          name: "Equity data",
          exact: true,
        }),
      ).toHaveCount(0);
      await expect(
        newAuthenticatedPage.getByText("Preset code / version", { exact: true }),
      ).toHaveCount(0);
      for (const label of [
        "Net return",
        "Maximum drawdown",
        "Win rate",
        "Profit factor",
        "Executed trades",
        "Price action",
        "Equity progression",
      ]) {
        await expect(newAuthenticatedPage.getByText(label, { exact: true }).first()).toBeVisible();
      }
      await expect(
        newAuthenticatedPage.getByRole("img", {
          name: /Candlestick chart for .* hypothetical trades and buy and sell markers/,
        }),
      ).toBeVisible();
      await expect(
        newAuthenticatedPage.getByRole("button", {
          name: `Expand ${manifest.symbol} chart`,
          exact: true,
        }),
      ).toBeVisible();
      await newAuthenticatedPage
        .getByRole("button", {
          name: `Expand ${manifest.symbol} chart`,
          exact: true,
        })
        .click();
      await expect(newAuthenticatedPage.getByRole("dialog")).toBeVisible();
      await expect(
        newAuthenticatedPage.getByRole("dialog").getByRole("img", {
          name: /Candlestick chart for .* hypothetical trades and buy and sell markers/,
        }),
      ).toBeVisible();
      await newAuthenticatedPage
        .getByRole("dialog")
        .getByRole("button", { name: "Close" })
        .click();
      await newAuthenticatedPage.getByRole("tab", { name: "Methodology", exact: true }).click();
      const visibleReportPanel = newAuthenticatedPage.locator(
        '[data-slot="tabs-content"][data-state="active"]',
      );
      await visibleReportPanel
        .getByText("View dataset and result fingerprints", { exact: true })
        .click();
      await expect(
        visibleReportPanel.getByText("Dataset fingerprint", { exact: true }),
      ).toBeVisible();
      await expect(visibleReportPanel.getByText("UTC", { exact: false }).first()).toBeVisible();
    });
  }

  test("analysis-missing-coverage fails through the worker without a report", async ({
    appApi,
    authenticatedSession,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const manifest = HISTORICAL_SCENARIOS["analysis-missing-coverage"];
    const fixture = await createScenario(
      e2eControl,
      authenticatedSession.userId,
      "analysis-missing-coverage",
    );
    const runId = String(fixture.runId);
    const result = await waitForHistoricalStatus(appApi, runId, "failed");
    expect((result.run as { failureCode?: string }).failureCode).toBe("historical_dataset_gap_detected");

    await newAuthenticatedPage.goto("/historical-analysis");
    await selectScenarioRun(newAuthenticatedPage, manifest.symbol);
    await expect(newAuthenticatedPage.getByText("Stored candle history contains a gap in the selected analysis coverage.", { exact: true })).toBeVisible();
    await expect(
      newAuthenticatedPage.getByRole("tab", { name: "Methodology", exact: true }),
    ).toHaveCount(0);
  });

  test("analysis-paginated preserves ordered trade and equity pages", async ({
    appApi,
    authenticatedSession,
    e2eControl,
    newAuthenticatedPage,
  }) => {
    const manifest = HISTORICAL_SCENARIOS["analysis-paginated"];
    const fixture = await createScenario(e2eControl, authenticatedSession.userId, "analysis-paginated");
    const runId = String(fixture.runId);
    await waitForHistoricalStatus(appApi, runId, "succeeded");

    const tradeSequences: number[] = [];
    let tradeCursor: string | undefined;
    do {
      const page = await appApi.getHistoricalTrades(runId, tradeCursor);
      tradeSequences.push(
        ...((page.trades as Array<{ sequence: number }> | undefined) ?? []).map(
          (trade) => trade.sequence,
        ),
      );
      tradeCursor = (page.nextCursor as string | null | undefined) ?? undefined;
    } while (tradeCursor);
    expect(tradeSequences.length).toBeGreaterThanOrEqual(
      manifest.expected.tradeCount.minimum,
    );
    expect(new Set(tradeSequences).size).toBe(tradeSequences.length);
    expect(tradeSequences).toEqual([...tradeSequences].sort((left, right) => left - right));

    const equitySequences: number[] = [];
    let equityCursor: string | undefined;
    do {
      const page = await appApi.getHistoricalEquity(runId, equityCursor);
      equitySequences.push(
        ...((page.equity as Array<{ sequence: number }> | undefined) ?? []).map(
          (point) => point.sequence,
        ),
      );
      equityCursor = (page.nextCursor as string | null | undefined) ?? undefined;
    } while (equityCursor);
    expect(equitySequences.length).toBeGreaterThan(200);
    expect(new Set(equitySequences).size).toBe(equitySequences.length);

    await newAuthenticatedPage.goto("/historical-analysis");
    await selectScenarioRun(newAuthenticatedPage, manifest.symbol);
    await newAuthenticatedPage.getByRole("tab", { name: "Hypothetical trades", exact: true }).click();
    const activeReportPanel = newAuthenticatedPage.locator(
      '[data-slot="tabs-content"][data-state="active"]',
    );
    await expect(
      activeReportPanel.getByText("Immutable hypothetical trades, ordered by sequence.", { exact: false }).first(),
    ).toBeVisible();
    const loadTrades = activeReportPanel.getByRole("button", { name: "Load more trades", exact: true });
    if (await loadTrades.isVisible()) {
      await loadTrades.click();
    }
  });
});

function expectMetricCount(
  actual: string | number | null,
  expected: { minimum: number; exact?: number },
) {
  const count = Number(actual);
  if (expected.exact !== undefined) {
    expect(count).toBe(expected.exact);
    return;
  }
  expect(count).toBeGreaterThanOrEqual(expected.minimum);
}

function expectMetricSign(
  actual: string | number | null,
  expected: "positive" | "negative" | "zero",
) {
  const value = String(actual);
  if (expected === "positive") {
    expect(value).toMatch(/^(?!-)(?=.*[1-9])\d/);
    return;
  }
  if (expected === "negative") {
    expect(value).toMatch(/^-\d/);
    return;
  }
  expect(value).toMatch(/^0(?:\.0+)?$/);
}

function expectDrawdownSign(
  actual: string | number | null,
  expected: "positive" | "zero",
) {
  const value = String(actual);
  if (expected === "positive") {
    expect(value).toMatch(/^-\d(?=.*[1-9])/);
    return;
  }
  expect(value).toMatch(/^0(?:\.0+)?$/);
}
