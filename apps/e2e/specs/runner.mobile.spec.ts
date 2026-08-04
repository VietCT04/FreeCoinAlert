import { expect, test } from "../fixtures/test";
import { AuthPage } from "../pages/auth.page";

test("the mobile runner can reach the sign-in form", async ({ page, checkAccessibility }) => {
  const authPage = new AuthPage(page);
  await authPage.gotoSignIn();

  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign up", exact: true })).toBeVisible();

  const accessibility = await checkAccessibility("mobile-sign-in");
  expect(accessibility.violations).toEqual([]);
});
