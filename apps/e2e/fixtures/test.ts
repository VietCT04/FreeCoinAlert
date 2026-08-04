import { test as base, expect, type Page } from "@playwright/test";

import { AuthPage } from "../pages/auth.page";
import {
  collectAccessibilityResults,
  type AccessibilityResult,
} from "../support/accessibility";
import { E2EControl } from "../support/e2e-control";
import { ProviderControl } from "../support/provider-control";
import { createTestUser, type TestUser } from "./users";
import { waitForBusinessState, waitForPath } from "../support/waits";

type WaitHelpers = {
  forBusinessState: (text: string) => Promise<void>;
  forPath: (path: string) => Promise<void>;
};

type E2EFixtures = {
  testUser: TestUser;
  providerControl: ProviderControl;
  e2eControl: E2EControl;
  waits: WaitHelpers;
  checkAccessibility: (label: string) => Promise<AccessibilityResult>;
  authenticatedPage: Page;
};

export const test = base.extend<E2EFixtures>({
  testUser: async ({}, use, testInfo) => {
    await use(createTestUser(testInfo));
  },
  providerControl: async ({ request }, use) => {
    await use(new ProviderControl(request));
  },
  e2eControl: async ({ request }, use) => {
    await use(new E2EControl(request));
  },
  waits: async ({ page }, use) => {
    await use({
      forBusinessState: (text) => waitForBusinessState(page, text),
      forPath: (path) => waitForPath(page, path),
    });
  },
  checkAccessibility: async ({ page }, use, testInfo) => {
    await use((label) => collectAccessibilityResults(page, testInfo, label));
  },
  authenticatedPage: async ({ page, testUser }, use) => {
    const authPage = new AuthPage(page);
    await authPage.gotoSignUp();
    await authPage.register(testUser);
    await use(page);
  },
});

export { expect };
