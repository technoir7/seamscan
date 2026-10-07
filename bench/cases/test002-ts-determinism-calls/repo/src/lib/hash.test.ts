import { describe, expect, it } from "vitest";
import { cacheKey, stableStringify } from "./hash";

describe("cacheKey", () => {
  it("is deterministic for the same input", () => {
    const input = { b: 2, a: [1, 2, 3] };
    expect(cacheKey(input)).toBe(cacheKey(input));
  });

  it("ignores key order", () => {
    expect(stableStringify({ a: 1, b: 2 })).toEqual(stableStringify({ b: 2, a: 1 }));
  });

  it("returns a fresh object each call", () => {
    expect(structuredClone({ a: 1 })).not.toBe(structuredClone({ a: 1 }));
  });
});
