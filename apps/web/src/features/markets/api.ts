import type { SupportedMarketsEnvelope } from "./types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function getApiUrl(path: string): string {
  if (!apiBaseUrl) {
    throw new Error("The browser API URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}

export async function getSupportedMarkets(): Promise<SupportedMarketsEnvelope> {
  const response = await fetch(getApiUrl("/markets"), {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Supported market request failed.");
  }

  return (await response.json()) as SupportedMarketsEnvelope;
}
