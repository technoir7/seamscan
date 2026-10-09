import { describe, expect, it } from "vitest";
import { relative } from "./relative";

describe("relative", () => {
  it("says today", () => {
    expect(relative(new Date(), new Date())).toBe("today");
  });

  it.skip("says yesterday across midnight", () => {
    expect(relative(new Date("2026-01-02T00:10:00"), new Date("2026-01-01T23:50:00"))).toBe("yesterday");
  });
});
