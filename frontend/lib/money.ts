const MONEY_PATTERN = /^(?:0|[1-9]\d*)(?:\.(\d{1,2}))?$/;

export function parseRupeesToPaise(input: string): number {
  const normalized = input.trim().replace(/^₹\s*/, "");
  if (!MONEY_PATTERN.test(normalized)) {
    throw new Error("Invalid money amount");
  }

  const [rupees, paise = ""] = normalized.split(".");
  const paddedPaise = paise.padEnd(2, "0");
  const value = Number.parseInt(rupees, 10) * 100 + Number.parseInt(paddedPaise || "0", 10);

  if (!Number.isSafeInteger(value) || value < 0) {
    throw new Error("Invalid money amount");
  }

  return value;
}

export function formatPaise(paise: number): string {
  const sign = paise < 0 ? "-" : "";
  const absolute = Math.abs(paise);
  const rupees = Math.floor(absolute / 100);
  const cents = String(absolute % 100).padStart(2, "0");
  return `${sign}₹${rupees}.${cents}`;
}
