import { describe, expect, it } from "vitest";
import { readCache, writeCache } from "./fs-cache";

describe("fs cache", () => {
  it("round-trips a value", async () => {
    await writeCache("k", { v: 1 });
    expect(await readCache("k")).toEqual({ v: 1 });
  });
});
