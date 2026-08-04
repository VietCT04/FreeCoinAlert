import { createHash } from "node:crypto";

import type { TestInfo } from "@playwright/test";

export type TestUser = {
  email: string;
  password: string;
};

function safePart(value: string, maximumLength: number): string {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return normalized.replace(/^-+|-+$/g, "").slice(0, maximumLength) || "test";
}

export function createTestUser(testInfo: TestInfo): TestUser {
  const runId = safePart(process.env.E2E_RUN_ID || "local-run", 24);
  const testId = safePart(testInfo.testId, 40);
  const suffix = createHash("sha256")
    .update(`${process.env.E2E_RUN_ID || "local-run"}:${testInfo.testId}`)
    .digest("hex")
    .slice(0, 12);

  return {
    email: `e2e+${runId}-${testId}-${suffix}@example.test`,
    password: "E2E-test-password-2026!",
  };
}
