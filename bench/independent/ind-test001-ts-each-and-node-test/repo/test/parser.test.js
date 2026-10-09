import test from "node:test";
import assert from "node:assert/strict";
import { parseRange } from "../lib/parser.js";

const cases = ["1-3", "4-9", "10-10"];

test("parses a simple range", () => {
  assert.deepEqual(parseRange("1-3"), [1, 2, 3]);
});

test("parses every sample range", async (t) => {
  for (const c of cases) {
    parseRange(c);
  }
});
