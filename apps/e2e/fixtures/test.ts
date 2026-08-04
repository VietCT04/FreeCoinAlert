import {
  test as base,
  expect,
  type BrowserContext,
  type Page,
} from "@playwright/test";

import { AuthPage } from "../pages/auth.page";
import { AppApi } from "../support/app-api";
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
  appApi: AppApi;
  authenticatedSession: AuthenticatedSession;
  newAnonymousPage: Page;
  newAuthenticatedPage: Page;
  connectedTelegramPage: Page;
  providerControl: ProviderControl;
  providerSimulator: ProviderControl;
  e2eControl: E2EControl;
  waits: WaitHelpers;
  checkAccessibility: (label: string) => Promise<AccessibilityResult>;
  authenticatedPage: Page;
};

export type AuthenticatedSession = {
  context: BrowserContext;
  page: Page;
  userId: string;
  csrfToken: string;
};

export const test = base.extend<E2EFixtures>({
  testUser: async ({}, use, testInfo) => {
    await use(createTestUser(testInfo));
  },
  appApi: async ({ playwright }, use) => {
    const request = await playwright.request.newContext({
      baseURL: "http://api:8000",
      extraHTTPHeaders: { Origin: "http://web:3000" },
    });
    await use(new AppApi(request));
    await request.dispose();
  },
  authenticatedSession: async ({ appApi, browser, testUser }, use) => {
    const authentication = await appApi.register(testUser);
    const context = await browser.newContext({
      storageState: await appApi.storageState(),
    });
    const page = await context.newPage();
    await use({
      context,
      page,
      userId: authentication.user.id,
      csrfToken: authentication.csrfToken,
    });
    await context.close();
  },
  newAnonymousPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
  newAuthenticatedPage: async ({ authenticatedSession }, use) => {
    await use(authenticatedSession.page);
  },
  providerSimulator: async ({ request }, use) => {
    const control = new ProviderControl(request);
    await control.reset();
    await use(control);
  },
  providerControl: async ({ providerSimulator }, use) => {
    await use(providerSimulator);
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
  connectedTelegramPage: async ({ newAuthenticatedPage, providerSimulator }, use) => {
    await newAuthenticatedPage.goto("/telegram");

    const popupPromise = newAuthenticatedPage.waitForEvent("popup");
    await newAuthenticatedPage
      .getByRole("button", { name: "Connect Telegram", exact: true })
      .click();
    const popup = await popupPromise;
    await popup.waitForLoadState("domcontentloaded");
    await expect(popup.getByText("E2E Telegram simulator", { exact: true })).toBeVisible();
    await popup.close();

    await expect(
      newAuthenticatedPage.getByText("Connected", { exact: true }),
    ).toBeVisible();
    await use(newAuthenticatedPage);
    await providerSimulator.reset();
  },
});

export { expect };
