const DEFAULT_DEVELOPMENT_SITE_URL = "http://localhost:3000";

type SiteEnvironment = "development" | "test" | "production";

function isPrivateDevelopmentHost(hostname: string): boolean {
  const normalizedHostname = hostname.replace(/^\[|\]$/g, "").toLowerCase();

  if (
    normalizedHostname === "localhost" ||
    normalizedHostname.endsWith(".localhost") ||
    normalizedHostname.endsWith(".test") ||
    normalizedHostname.endsWith(".local") ||
    normalizedHostname === "0.0.0.0" ||
    normalizedHostname === "::1"
  ) {
    return true;
  }

  const octets = normalizedHostname.split(".").map(Number);
  if (
    octets.length !== 4 ||
    octets.some((octet) => !Number.isInteger(octet) || octet < 0 || octet > 255)
  ) {
    return false;
  }

  const [first, second] = octets;
  return (
    first === 0 ||
    first === 10 ||
    first === 127 ||
    (first === 169 && second === 254) ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168)
  );
}

function getDevelopmentDefaultSiteUrl(environment: SiteEnvironment): string {
  if (environment === "development") {
    return DEFAULT_DEVELOPMENT_SITE_URL;
  }

  throw new Error("SITE_URL must be configured outside development.");
}

export function normalizeSiteUrl(
  configuredSiteUrl: string | undefined,
  environment: SiteEnvironment =
    (process.env.NODE_ENV as SiteEnvironment | undefined) ?? "development",
): string {
  const rawSiteUrl =
    configuredSiteUrl?.trim() || getDevelopmentDefaultSiteUrl(environment);

  if (!/^https?:\/\/[^/?#]+\/?$/.test(rawSiteUrl)) {
    throw new Error(
      "SITE_URL must be an absolute origin without a path, query, or fragment.",
    );
  }

  let parsedSiteUrl: URL;

  try {
    parsedSiteUrl = new URL(rawSiteUrl);
  } catch {
    throw new Error("SITE_URL must be an absolute http(s) origin.");
  }

  if (!/^https?:$/.test(parsedSiteUrl.protocol)) {
    throw new Error("SITE_URL must use http or https.");
  }

  if (
    parsedSiteUrl.username ||
    parsedSiteUrl.password ||
    parsedSiteUrl.search ||
    parsedSiteUrl.hash ||
    (parsedSiteUrl.pathname !== "" && parsedSiteUrl.pathname !== "/")
  ) {
    throw new Error(
      "SITE_URL must not include a path, query, fragment, username, or password.",
    );
  }

  if (!parsedSiteUrl.hostname) {
    throw new Error("SITE_URL must include a hostname.");
  }

  if (environment === "production") {
    if (parsedSiteUrl.protocol !== "https:") {
      throw new Error("Production SITE_URL must use https.");
    }

    if (isPrivateDevelopmentHost(parsedSiteUrl.hostname)) {
      throw new Error("Production SITE_URL must use a public hostname.");
    }
  }

  return parsedSiteUrl.origin;
}

export const SITE_URL = normalizeSiteUrl(
  process.env.SITE_URL,
  (process.env.NODE_ENV as SiteEnvironment | undefined) ?? "development",
);

export const SEO_INDEXING_ENABLED = process.env.SEO_INDEXING_ENABLED === "true";
