import { createHash, randomBytes } from "node:crypto";
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
  const runIdentifier = process.env.E2E_RUN_ID || "local-run";
  const runId = safePart(runIdentifier, 12);
  const runHash = createHash("sha256")
    .update(runIdentifier)
    .digest("hex")
    .slice(0, 8);
  const testFile = safePart(basename(testInfo.file, ".spec.ts"), 16);
  const testHash = createHash("sha256")
    .update(testInfo.testId)
    .digest("hex")
    .slice(0, 16);

  return {
    email: `e2e+${runId}-${runHash}-${testFile}-${testHash}@example.com`,
    password: `${randomBytes(18).toString("base64url")}Aa1!`,
  };
}
