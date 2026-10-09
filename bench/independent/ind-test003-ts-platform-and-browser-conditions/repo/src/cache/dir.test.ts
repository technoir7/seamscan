import { describe, expect, it } from "vitest";
import { cacheDir } from "./dir";

const isWindows = process.platform === "win32";
const itPosix = process.platform === "win32" ? it.skip : it;

describe.skipIf(process.platform === "win32")("symlinked cache dir", () => {
  it("resolves symlinks", () => {
    expect(cacheDir()).toBeTruthy();
  });
});

it.runIf(!isWindows)("uses a unix socket", () => {
  expect(cacheDir()).toContain("/");
});

itPosix("handles a trailing slash", () => {
  expect(cacheDir()).not.toMatch(/\\$/);
});
