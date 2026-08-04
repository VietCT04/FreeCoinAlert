import AxeBuilder from "@axe-core/playwright";
import type { Page, TestInfo } from "@playwright/test";

import { attachRedactedJson } from "./attachments";

export type AccessibilityResult = {
  violations: unknown[];
};

export async function collectAccessibilityResults(
  page: Page,
  testInfo: TestInfo,
  label: string,
): Promise<AccessibilityResult> {
  const results = await new AxeBuilder({ page }).analyze();
  await attachRedactedJson(testInfo, `accessibility-${label}`, results);
  return results;
}
