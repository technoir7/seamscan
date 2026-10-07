import { describe, expect, it } from "vitest";
import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it.skip("renders footnotes", () => {
    const html = renderMarkdown("a[^1]\n\n[^1]: b");
    expect(html).toContain('<section class="footnotes">');
  });
});
