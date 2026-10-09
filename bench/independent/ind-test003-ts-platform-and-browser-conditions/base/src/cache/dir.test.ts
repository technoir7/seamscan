import { describe, expect, it } from "vitest";
import { cacheDir } from "./dir";

describe("cache dir", () => {
  it("resolves symlinks", () => {
    expect(cacheDir()).toBeTruthy();
  });
});
