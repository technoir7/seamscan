import { it, expect } from "vitest";

it("compares", () => {
  const password = "admin123";
  expect(password === "admin123").toBe(true);
});
