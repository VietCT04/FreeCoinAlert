import { expect, type Locator, type Page } from "@playwright/test";

export async function waitForBusinessState(
  target: Page | Locator,
  text: string,
): Promise<void> {
  const locator = target.getByText(text, { exact: true });
  await expect(locator).toBeVisible();
}

export async function waitForPath(page: Page, path: string): Promise<void> {
  await expect(page).toHaveURL(new RegExp(`${path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`));
}
