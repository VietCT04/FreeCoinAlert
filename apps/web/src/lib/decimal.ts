const PLAIN_DECIMAL_PATTERN = /^[+-]?\d+(?:\.\d+)?$/;

export function formatExactDecimal(value: string): string {
  if (!PLAIN_DECIMAL_PATTERN.test(value)) {
    return value;
  }

  const sign = value.startsWith("-") || value.startsWith("+") ? value[0] : "";
  const unsigned = sign ? value.slice(1) : value;
  const [integerPart, fractionPart = ""] = unsigned.split(".");
  const integer = integerPart.replace(/^0+(?=\d)/, "") || "0";
  const fraction = fractionPart.replace(/0+$/, "");
  const normalized = fraction ? `${integer}.${fraction}` : integer;

  return normalized === "0" ? "0" : `${sign}${normalized}`;
}
