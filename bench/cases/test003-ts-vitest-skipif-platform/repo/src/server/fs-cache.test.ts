import os from "node:os";
import { describe, expect, it } from "vitest";
import { readCache, writeCache } from "./fs-cache";

const isWindows = process.platform === "win32";

describe("fs cache", () => {
  it("round-trips a value", async () => {
    await writeCache("k", { v: 1 });
    expect(await readCache("k")).toEqual({ v: 1 });
  });

  it.runIf(!isWindows)("writes the cache file with mode 0600", async () => {
    await writeCache("k", { v: 1 });
    expect(await readCache("k")).toEqual({ v: 1 });
  });
});

describe.skipIf(process.platform === "win32" || os.arch() === "arm64")("symlinked cache dir", () => {
  it("follows the symlink", async () => {
    expect(await readCache("linked")).toBeNull();
  });
});
