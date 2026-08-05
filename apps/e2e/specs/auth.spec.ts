import { AuthPage } from "../pages/auth.page";
import { expect, test } from "../fixtures/test";
import { E2E_API_ORIGIN, E2E_WEB_ORIGIN } from "../support/urls";

test.describe("authentication", () => {
  test("redirects anonymous users from every protected dashboard route", async ({ newAnonymousPage }) => {
    const authPage = new AuthPage(newAnonymousPage);

    for (const route of [
      "/dashboard",
      "/price-alerts",
      "/preset-signals",
      "/historical-analysis",
      "/telegram",
    ]) {
      await newAnonymousPage.goto(route);
      await expect(newAnonymousPage).toHaveURL(/\/sign-in$/);
      await expect(newAnonymousPage.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
    }

    await authPage.gotoSignUp();
    await expect(newAnonymousPage.getByRole("heading", { name: "Create an account", exact: true })).toBeVisible();
  });

  test("enforces sign-up validation and creates an account through the form", async ({ page, testUser }) => {
    const authPage = new AuthPage(page);
    await authPage.gotoSignUp();

    await expect(page.getByLabel("Email")).toHaveAttribute("required", "");
    await expect(page.getByLabel("Password", { exact: true })).toHaveAttribute("required", "");
    await expect(page.getByLabel("Confirm password")).toHaveAttribute("required", "");

    await page.getByLabel("Email").fill(testUser.email);
    await page.getByLabel("Password", { exact: true }).fill("short");
    await page.getByLabel("Confirm password").fill("different-password");
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await expect(authPage.error("Password must be between 15 and 128 characters.")).toBeVisible();

    await page.getByLabel("Password", { exact: true }).fill(testUser.password);
    await page.getByLabel("Confirm password").fill("different-password");
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await expect(authPage.error("Passwords must match.")).toBeVisible();

    await authPage.submitSignUp(testUser);
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("rejects a duplicate normalized email without exposing account details", async ({ page, testUser }) => {
    const authPage = new AuthPage(page);
    await authPage.gotoSignUp();
    await authPage.submitSignUp(testUser);
    await expect(page).toHaveURL(/\/dashboard$/);
    await authPage.signOut();

    await authPage.gotoSignUp();
    await page.getByLabel("Email").fill(` ${testUser.email.toUpperCase()} `);
    await page.getByLabel("Password", { exact: true }).fill(testUser.password);
    await page.getByLabel("Confirm password").fill(testUser.password);
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await expect(authPage.error("An account cannot be created with these details. Try signing in or use a different email.")).toBeVisible();
  });

  test("supports bad credentials, correct credentials, sign-out, and reload restoration", async ({ page, testUser }) => {
    const authPage = new AuthPage(page);
    await authPage.gotoSignUp();
    await authPage.submitSignUp(testUser);
    await expect(page).toHaveURL(/\/dashboard$/);
    await authPage.signOut();

    await authPage.gotoSignIn();
    await authPage.submitSignIn({ ...testUser, password: `${testUser.password}-wrong` });
    await expect(authPage.error("Email or password is incorrect.")).toBeVisible();

    await authPage.submitSignIn(testUser);
    await expect(page).toHaveURL(/\/dashboard$/);
    await page.reload();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();

    await authPage.signOut();
    await expect(page).toHaveURL(/\/sign-in$/);
  });

  test("redirects the next browser action after a second request context logs out", async ({
    authenticatedSession,
    browser,
    newAuthenticatedPage,
    playwright,
    testUser,
  }) => {
    await newAuthenticatedPage.goto("/dashboard");
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();

    const secondRequest = await playwright.request.newContext({
      baseURL: E2E_API_ORIGIN,
      extraHTTPHeaders: { Origin: E2E_WEB_ORIGIN },
      storageState: await authenticatedSession.context.storageState(),
    });
    try {
      const logoutResponse = await secondRequest.post("/auth/logout", {
        headers: { "X-CSRF-Token": authenticatedSession.csrfToken },
      });
      expect(logoutResponse.status()).toBe(204);
    } finally {
      await secondRequest.dispose();
    }

    await newAuthenticatedPage.reload();
    await expect(newAuthenticatedPage).toHaveURL(/\/sign-in$/);
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
    expect(await authenticatedSession.context.storageState()).toBeTruthy();
    expect(await browser.contexts()).toContain(authenticatedSession.context);
  });

  test("does not leave authentication or CSRF state in browser storage after sign-out", async ({
    page,
    testUser,
  }) => {
    const authPage = new AuthPage(page);
    await authPage.gotoSignUp();
    await authPage.submitSignUp(testUser);
    await expect(page).toHaveURL(/\/dashboard$/);
    await authPage.signOut();

    const storageKeys = await page.evaluate(() => [localStorage, sessionStorage].flatMap((storage) => Object.keys(storage)));
    expect(storageKeys.some((key) => /session|csrf|telegram|signal|alert/i.test(key))).toBeFalsy();
  });
});
