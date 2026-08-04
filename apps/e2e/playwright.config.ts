import { defineConfig, devices } from "@playwright/test";
import { join } from "node:path";

const artifactDirectory = process.env.E2E_ARTIFACT_DIR || "/artifacts/e2e";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  actionTimeout: 10_000,
  navigationTimeout: 20_000,
  reporter: [
    ["line"],
    ["html", { outputFolder: join(artifactDirectory, "playwright-report"), open: "never" }],
    ["json", { outputFile: join(artifactDirectory, "results.json") }],
  ],
  outputDir: join(artifactDirectory, "test-results"),
  use: {
    baseURL: "http://web:3000",
    timezoneId: "UTC",
    locale: "en-US",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-desktop",
      testIgnore: "**/*.mobile.spec.ts",
      use: {
        ...devices["Desktop Chrome"],
        browserName: "chromium",
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "chromium-mobile",
      testMatch: "**/*.mobile.spec.ts",
      use: {
        ...devices["Pixel 7"],
        browserName: "chromium",
      },
    },
  ],
});
