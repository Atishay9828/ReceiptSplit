import { describe, expect, it } from "vitest";

import { formatPaise, parseRupeesToPaise } from "@/lib/money";

describe("money conversion", () => {
  it("converts rupee strings to integer paise", () => {
    expect(parseRupeesToPaise("120.50")).toBe(12050);
    expect(parseRupeesToPaise("100")).toBe(10000);
    expect(parseRupeesToPaise("0.05")).toBe(5);
  });

  it("rejects invalid rupee strings", () => {
    expect(() => parseRupeesToPaise("12.345")).toThrow("Invalid money amount");
    expect(() => parseRupeesToPaise("-1")).toThrow("Invalid money amount");
    expect(() => parseRupeesToPaise("abc")).toThrow("Invalid money amount");
  });

  it("formats paise as rupees", () => {
    expect(formatPaise(12050)).toBe("₹120.50");
    expect(formatPaise(10000)).toBe("₹100.00");
  });
});
