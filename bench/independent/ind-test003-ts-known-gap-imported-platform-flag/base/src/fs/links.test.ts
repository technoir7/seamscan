import { expect, it } from "vitest";
import { makeLink } from "./links";

it("creates a symlink", () => {
  expect(makeLink("a", "b")).toBe(true);
});
