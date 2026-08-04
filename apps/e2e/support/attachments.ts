import type { TestInfo } from "@playwright/test";

const REDACTED = "[REDACTED]";
const SENSITIVE_KEY = /password|cookie|csrf|token|authorization|telegramchatid|telegramuserid/i;

function redact(value: unknown, key?: string): unknown {
  if (key && SENSITIVE_KEY.test(key)) {
    return REDACTED;
  }

  if (Array.isArray(value)) {
    return value.map((item) => redact(item));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([entryKey, entryValue]) => [
        entryKey,
        redact(entryValue, entryKey),
      ]),
    );
  }

  return value;
}

export async function attachRedactedJson(
  testInfo: TestInfo,
  name: string,
  value: unknown,
): Promise<void> {
  await testInfo.attach(name, {
    body: Buffer.from(JSON.stringify(redact(value), null, 2), "utf8"),
    contentType: "application/json",
  });
}
