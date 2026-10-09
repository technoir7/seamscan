import { describe, expect, it } from "vitest";
import { formatCents } from "./money";

describe("formatCents", () => {
  it("formats whole dollars", () => {
    expect(formatCents(500)).toBe("$5.00");
  });

  it("formats currency for de-DE", () => {
    const out = formatCents(123456, "de-DE");
    console.log("de-DE:", out);
  });
});
