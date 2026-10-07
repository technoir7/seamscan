import { describe, expect, it } from "vitest";
import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it.skip("renders footnotes", () => {
    expect(renderMarkdown("a[^1]\n\n[^1]: b")).toContain("footnote");
  });
});
