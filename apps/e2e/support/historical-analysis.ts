import { expect, type Page } from "@playwright/test";

import type { AppApi } from "./app-api";

export async function waitForHistoricalStatus(
  appApi: AppApi,
  runId: string,
  status: string,
): Promise<Record<string, unknown>> {
  await expect
    .poll(
      async () => {
        const response = await appApi.getHistoricalAnalysis(runId);
        return (response.run as { status?: string } | undefined)?.status;
      },
      { timeout: 120_000 },
    )
    .toBe(status);
  return appApi.getHistoricalAnalysis(runId);
}

export async function expectNoPageOverflow(page: Page): Promise<void> {
  const hasOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  if (hasOverflow) {
    throw new Error("The page has horizontal overflow at the approved mobile viewport.");
  }
}
