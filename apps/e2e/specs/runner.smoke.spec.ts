import { DashboardPage } from "../pages/dashboard.page";
import { expect, test } from "../fixtures/test";

test("the isolated runner can register and reach the authenticated dashboard", async ({
  authenticatedPage,
  checkAccessibility,
}) => {
  const dashboard = new DashboardPage(authenticatedPage);
  await expect(authenticatedPage).toHaveURL(/\/dashboard$/);
  await expect(dashboard.heading()).toBeVisible();

  const accessibility = await checkAccessibility("authenticated-dashboard");
  expect(accessibility.violations).toEqual([]);
});
