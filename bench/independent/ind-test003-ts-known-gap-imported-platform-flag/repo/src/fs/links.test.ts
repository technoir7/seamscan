import { expect, it } from "vitest";
import { isWindows } from "../env";
import { makeLink } from "./links";

it.skipIf(isWindows)("creates a symlink", () => {
  expect(makeLink("a", "b")).toBe(true);
});
