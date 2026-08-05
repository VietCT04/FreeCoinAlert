import { expect, test } from "../fixtures/test";

test.describe("mobile dashboard shell", () => {
  test("opens a focus-contained drawer, navigates every destination, and returns focus on Escape", async ({
    checkAccessibility,
    newAuthenticatedPage,
  }) => {
    await newAuthenticatedPage.goto("/dashboard");
    const trigger = newAuthenticatedPage.getByRole("button", { name: "Open navigation", exact: true });
    await trigger.click();

    const drawer = newAuthenticatedPage.getByRole("dialog", { name: "Sidebar", exact: true });
    await expect(drawer).toBeVisible();
    for (const label of ["Overview", "Price Alerts", "Preset Signals", "Historical Analysis", "Telegram"]) {
      await expect(drawer.getByRole("link", { name: label, exact: true })).toBeVisible();
    }

    await newAuthenticatedPage.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
    await expect(trigger).toBeFocused();

    await trigger.click();
    await drawer.getByRole("link", { name: "Telegram", exact: true }).click();
    await expect(newAuthenticatedPage).toHaveURL(/\/telegram$/);

    for (const [label, path] of [
      ["Overview", "/dashboard"],
      ["Price Alerts", "/price-alerts"],
      ["Preset Signals", "/preset-signals"],
      ["Historical Analysis", "/historical-analysis"],
      ["Telegram", "/telegram"],
    ] as const) {
      await trigger.click();
      const openDrawer = newAuthenticatedPage.getByRole("dialog", { name: "Sidebar", exact: true });
      await openDrawer.getByRole("link", { name: label, exact: true }).click();
      await expect(newAuthenticatedPage).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
      await trigger.click();
      const currentLink = newAuthenticatedPage
        .getByRole("dialog", { name: "Sidebar", exact: true })
        .getByRole("link", { name: label, exact: true });
      await expect(currentLink).toHaveAttribute("aria-current", "page");
      await newAuthenticatedPage.keyboard.press("Escape");
    }

    const hasHorizontalOverflow = await newAuthenticatedPage.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasHorizontalOverflow).toBeFalsy();

    await expect(newAuthenticatedPage.getByRole("dialog", { name: "Sidebar", exact: true })).toBeHidden();
    await expect(newAuthenticatedPage.locator('[data-slot="sheet-overlay"]')).toBeHidden();
    const accessibility = await checkAccessibility("mobile-dashboard-shell", newAuthenticatedPage);
    expect(accessibility.violations).toEqual([]);
  });

  test("closes the drawer from an outside interaction and preserves the current destination announcement", async ({
    newAuthenticatedPage,
  }) => {
    await newAuthenticatedPage.goto("/price-alerts");
    const trigger = newAuthenticatedPage.getByRole("button", { name: "Open navigation", exact: true });
    await trigger.click();
    const drawer = newAuthenticatedPage.getByRole("dialog", { name: "Sidebar", exact: true });
    await expect(drawer.getByRole("link", { name: "Price Alerts", exact: true })).toHaveAttribute("aria-current", "page");

    const viewportWidth = newAuthenticatedPage.viewportSize()?.width ?? 390;
    await newAuthenticatedPage.locator('[data-slot="sheet-overlay"]').click({
      position: { x: viewportWidth - 8, y: 8 },
    });
    await expect(drawer).toBeHidden();
    await expect(newAuthenticatedPage.getByRole("heading", { name: "Price Alerts", exact: true })).toBeVisible();
  });
});
