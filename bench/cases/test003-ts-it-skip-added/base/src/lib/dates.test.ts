import { describe, expect, it } from "vitest";
import { formatRelative } from "./dates";

const now = new Date("2026-03-01T12:00:00Z");

describe("formatRelative", () => {
  it("says just now under a minute", () => {
    expect(formatRelative(new Date("2026-03-01T11:59:30Z"), now)).toBe("just now");
  });

  it("says yesterday across midnight", () => {
    expect(formatRelative(new Date("2026-02-28T23:00:00Z"), now)).toBe("yesterday");
  });
});
