import { expect, test } from "../fixtures/test";
import { expectNoPageOverflow } from "../support/historical-analysis";

test.describe("mobile public homepage SEO regressions", () => {
  test("keeps the marketing sheet, product preview, focus, and viewport stable", async ({
    newAnonymousPage,
  }) => {
    await newAnonymousPage.goto("/");

    const trigger = newAnonymousPage.getByRole("button", {
      name: "Open navigation",
      exact: true,
    });
    await expect(trigger).toBeVisible();
    await expect(newAnonymousPage.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(
      newAnonymousPage.getByRole("img", { name: /Example: XRPUSDT 1H strategy/i }),
    ).toBeVisible();
    await expectNoPageOverflow(newAnonymousPage);

    await trigger.click();
    const sheet = newAnonymousPage.getByRole("dialog", {
      name: "FreeCoinAlert navigation",
      exact: true,
    });
    await expect(sheet).toBeVisible();
    for (const label of ["Backtest", "Alerts", "Guides", "Sign in", "Start free"]) {
      await expect(sheet.getByRole("link", { name: label, exact: true })).toBeVisible();
    }
    await expectNoPageOverflow(newAnonymousPage);

    await newAnonymousPage.keyboard.press("Escape");
    await expect(sheet).toBeHidden();
    await expect(trigger).toBeFocused();
  });
});
