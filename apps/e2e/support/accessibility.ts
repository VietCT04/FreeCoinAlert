import AxeBuilder from "@axe-core/playwright";
import type { Page, TestInfo } from "@playwright/test";

import { attachRedactedJson } from "./attachments";

export type AccessibilityResult = {
  violations: AccessibilityViolation[];
};

export type AccessibilityViolation = {
  id: string;
  impact: string | null;
  help: string;
  helpUrl: string;
  targets: string[];
};

const MAX_VIOLATIONS = 50;
const MAX_TARGETS_PER_VIOLATION = 8;
const MAX_SELECTOR_LENGTH = 240;

function summarizeViolation(violation: {
  id: string;
  impact: string | null;
  help: string;
  helpUrl: string;
  nodes: Array<{ target: Array<string | string[]> }>;
}): AccessibilityViolation {
  return {
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    helpUrl: violation.helpUrl,
    targets: violation.nodes
      .flatMap((node) => node.target)
      .map((target) => (Array.isArray(target) ? target.join(" ") : target))
      .map((target) => target.slice(0, MAX_SELECTOR_LENGTH))
      .slice(0, MAX_TARGETS_PER_VIOLATION),
  };
}

export async function collectAccessibilityResults(
  page: Page,
  testInfo: TestInfo,
  label: string,
): Promise<AccessibilityResult> {
  const results = await new AxeBuilder({ page }).analyze();
  const summary = {
    violations: results.violations.slice(0, MAX_VIOLATIONS).map(summarizeViolation),
  };
  await attachRedactedJson(testInfo, `accessibility-${label}`, summary);
  return summary;
}

export function seriousAccessibilityViolations(
  result: AccessibilityResult,
): AccessibilityViolation[] {
  return result.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
}
