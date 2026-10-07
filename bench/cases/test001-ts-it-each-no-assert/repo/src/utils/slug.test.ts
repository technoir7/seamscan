import { describe, expect, it } from "vitest";
import { toSlug } from "./slug";

describe("toSlug", () => {
  it.each([
    ["Hello World", "hello-world"],
    ["  Crème Brûlée ", "creme-brulee"],
    ["Next.js & Supabase", "nextjs-supabase"],
  ])("turns %s into %s", (input, _expected) => {
    toSlug(input);
  });

  it("returns an empty string for blank input", () => {
    expect(toSlug("   ")).toBe("");
  });
});
