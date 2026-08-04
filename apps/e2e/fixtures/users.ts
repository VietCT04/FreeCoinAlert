import { randomBytes } from "node:crypto";
import { basename } from "node:path";

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
  const testFile = safePart(basename(testInfo.file, ".spec.ts"), 32);
  const testIndex = safePart(testInfo.testId, 64);

  return {
    email: `e2e+${runId}-${testFile}-${testIndex}@example.test`,
    password: `${randomBytes(18).toString("base64url")}Aa1!`,
  };
}
