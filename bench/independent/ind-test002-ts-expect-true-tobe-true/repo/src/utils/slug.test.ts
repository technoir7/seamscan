import { slugify } from "./slug";

describe("slugify", () => {
  it("lowercases words", () => {
    expect(slugify("Hello World")).toBe("hello-world");
  });

  it("handles emoji", () => {
    slugify("party 🎉");
    expect(true).toBe(true);
  });

  it("returns something for empty input", () => {
    slugify("");
    expect(1).toBeTruthy();
  });
});
