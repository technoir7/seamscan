import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCsv } from "../src/csv.js";

test("parses quoted commas", () => {
  assert.deepEqual(parseCsv('a,"b,c"\n'), [["a", "b,c"]]);
});

test("handles CRLF line endings", () => {
  assert.deepEqual(parseCsv("a,b\r\nc,d\r\n"), [["a", "b"], ["c", "d"]]);
});
