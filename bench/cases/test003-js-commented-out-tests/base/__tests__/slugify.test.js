import { slugify } from "../lib/slugify";

test("lower-cases words", () => {
  expect(slugify("Hello World")).toBe("hello-world");
});

test("strips emoji", () => {
  expect(slugify("Launch 🚀 day")).toBe("launch-day");
});

test("collapses repeated dashes", () => {
  expect(slugify("a -- b")).toBe("a-b");
});
