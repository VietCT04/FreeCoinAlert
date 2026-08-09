import { expect, test, type Page } from "../fixtures/test";
import { PUBLIC_SEO_ROUTES } from "../../web/src/lib/seo/routes";
import { E2E_WEB_ORIGIN } from "../support/urls";

const publicPaths = PUBLIC_SEO_ROUTES.map(({ path }) => path);
const privatePaths = [
  "/sign-in",
  "/sign-up",
  "/dashboard",
  "/price-alerts",
  "/preset-signals",
  "/historical-analysis",
  "/telegram",
] as const;

function absoluteUrl(path: string): string {
  return new URL(path, E2E_WEB_ORIGIN).toString();
}

async function readStructuredData(page: Page): Promise<unknown[]> {
  return page.locator('script[type="application/ld+json"]').evaluateAll((scripts) =>
    scripts.map((script) => JSON.parse(script.textContent ?? "")),
  );
}

function structuredTypes(data: readonly unknown[]): string[] {
  return data.flatMap((value) => {
    if (!value || typeof value !== "object") {
      return [];
    }

    const type = (value as { "@type"?: unknown })["@type"];
    return typeof type === "string" ? [type] : [];
  });
}

test.describe("public SEO surface", () => {
  test("renders unique metadata and one visible H1 for every public route", async ({
    newAnonymousPage,
  }) => {
    const titles: string[] = [];
    const descriptions: string[] = [];

    for (const path of publicPaths) {
      const response = await newAnonymousPage.goto(path);
      expect(response?.ok(), `${path} should load successfully`).toBe(true);
      await expect(newAnonymousPage.getByRole("heading", { level: 1 })).toHaveCount(1);

      const title = await newAnonymousPage.title();
      await expect(newAnonymousPage.locator('link[rel="canonical"]')).toHaveCount(1);
      await expect(newAnonymousPage.locator('meta[name="description"]')).toHaveCount(1);
      const description = await newAnonymousPage
        .locator('meta[name="description"]')
        .getAttribute("content");
      const canonical = await newAnonymousPage
        .locator('link[rel="canonical"]')
        .getAttribute("href");
      const robots = await newAnonymousPage
        .locator('meta[name="robots"]')
        .getAttribute("content");
      const openGraphUrl = await newAnonymousPage
        .locator('meta[property="og:url"]')
        .getAttribute("content");

      expect(title).not.toBe("");
      expect(description).toBeTruthy();
      expect(canonical).toBe(absoluteUrl(path));
      expect(robots).toMatch(/index/i);
      expect(robots).not.toMatch(/noindex/i);
      expect(openGraphUrl).toBe(canonical);
      await expect(newAnonymousPage.locator('meta[property="og:title"]')).toHaveAttribute(
        "content",
        /.+/,
      );
      await expect(newAnonymousPage.locator('meta[property="og:description"]')).toHaveAttribute(
        "content",
        /.+/,
      );
      await expect(newAnonymousPage.locator('meta[property="og:image"]')).toHaveAttribute(
        "content",
        /.+/,
      );
      await expect(newAnonymousPage.locator('meta[name="twitter:card"]')).toHaveAttribute(
        "content",
        "summary_large_image",
      );

      titles.push(title);
      descriptions.push(description ?? "");
    }

    expect(new Set(titles).size).toBe(titles.length);
    expect(new Set(descriptions).size).toBe(descriptions.length);
  });

  test("keeps the sitemap bounded to the public route registry", async ({
    newAnonymousPage,
  }) => {
    const response = await newAnonymousPage.request.get("/sitemap.xml");
    expect(response.ok()).toBe(true);
    const sitemap = await response.text();
    const sitemapUrls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(
      ([, url]) => url,
    );

    expect(new Set(sitemapUrls).size).toBe(sitemapUrls.length);
    expect(new Set(sitemapUrls)).toEqual(new Set(publicPaths.map(absoluteUrl)));
    expect(sitemapUrls.every((url) => new URL(url).origin === E2E_WEB_ORIGIN)).toBe(true);
    expect(sitemapUrls.every((url) => !/[?#]/.test(url))).toBe(true);
    expect(
      sitemapUrls.some((url) => privatePaths.some((path) => new URL(url).pathname === path)),
    ).toBe(false);
  });

  test("publishes the production-style robots policy in SEO E2E mode", async ({
    newAnonymousPage,
  }) => {
    const response = await newAnonymousPage.request.get("/robots.txt");
    expect(response.ok()).toBe(true);
    const robots = await response.text();

    expect(robots).toContain("User-agent: *");
    expect(robots).toContain("Allow: /");
    expect(robots).toContain(`Sitemap: ${absoluteUrl("/sitemap.xml")}`);
    expect(robots).not.toContain("Disallow: /");
    expect(robots).not.toContain("/_next/");
  });

  test("keeps authenticated routes noindex and out of the sitemap", async ({
    newAnonymousPage,
    newAuthenticatedPage,
  }) => {
    for (const path of ["/sign-in", "/sign-up"] as const) {
      await newAnonymousPage.goto(path);
      await expect(newAnonymousPage.locator('meta[name="robots"]')).toHaveAttribute(
        "content",
        /noindex/i,
      );
      await expect(newAnonymousPage.locator('meta[name="robots"]')).toHaveAttribute(
        "content",
        /nofollow/i,
      );
    }

    for (const path of privatePaths.slice(2)) {
      await newAuthenticatedPage.goto(path);
      const robots = await newAuthenticatedPage
        .locator('meta[name="robots"]')
        .getAttribute("content");
      expect(robots).toMatch(/noindex/i);
      expect(robots).toMatch(/nofollow/i);
    }
  });

  test("keeps the bounded public internal-link graph reachable", async ({
    newAnonymousPage,
  }) => {
    const targets = new Set<string>();

    for (const path of publicPaths) {
      await newAnonymousPage.goto(path);
      const hrefs = await newAnonymousPage
        .locator("main a[href], header a[href], footer a[href]")
        .evaluateAll((links) => links.map((link) => link.getAttribute("href")).filter(Boolean));

      for (const href of hrefs) {
        const url = new URL(href as string, E2E_WEB_ORIGIN);
        if (
          url.origin === E2E_WEB_ORIGIN &&
          !url.search &&
          !url.hash &&
          publicPaths.includes(url.pathname)
        ) {
          targets.add(url.pathname);
        }
      }
    }

    for (const target of targets) {
      const response = await newAnonymousPage.request.get(target);
      expect(response.ok(), `${target} should be reachable`).toBe(true);
    }
  });

  test("publishes only truthful structured data", async ({ newAnonymousPage }) => {
    await newAnonymousPage.goto("/");
    const homeData = await readStructuredData(newAnonymousPage);
    expect(structuredTypes(homeData)).toEqual(["WebSite"]);

    await newAnonymousPage.goto("/crypto-backtesting");
    const landingData = await readStructuredData(newAnonymousPage);
    expect(structuredTypes(landingData)).toContain("BreadcrumbList");

    await newAnonymousPage.goto("/guides");
    const hubData = await readStructuredData(newAnonymousPage);
    expect(structuredTypes(hubData)).toContain("BreadcrumbList");

    await newAnonymousPage.goto("/guides/rsi-backtesting");
    const guideData = await readStructuredData(newAnonymousPage);
    expect(structuredTypes(guideData)).toEqual(
      expect.arrayContaining(["BreadcrumbList", "Article"]),
    );

    for (const value of [...homeData, ...landingData, ...hubData, ...guideData]) {
      expect(value).toMatchObject({ "@context": "https://schema.org" });
      expect(JSON.stringify(value)).not.toMatch(/AggregateRating|Review/);
    }
  });
});
