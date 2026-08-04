import type { Page } from "@playwright/test";

import type { TestUser } from "../fixtures/users";

export class AuthPage {
  constructor(private readonly page: Page) {}

  async gotoSignIn(): Promise<void> {
    await this.page.goto("/sign-in");
  }

  async gotoSignUp(): Promise<void> {
    await this.page.goto("/sign-up");
  }

  async register(user: TestUser): Promise<void> {
    await this.page.getByLabel("Email").fill(user.email);
    await this.page.getByLabel("Password", { exact: true }).fill(user.password);
    await this.page.getByLabel("Confirm password").fill(user.password);
    await this.page.getByRole("button", { name: "Create account" }).click();
    await this.page.waitForURL("**/dashboard");
  }

  async signIn(user: TestUser): Promise<void> {
    await this.page.getByLabel("Email").fill(user.email);
    await this.page.getByLabel("Password", { exact: true }).fill(user.password);
    await this.page.getByRole("button", { name: "Sign in" }).click();
    await this.page.waitForURL("**/dashboard");
  }
}
