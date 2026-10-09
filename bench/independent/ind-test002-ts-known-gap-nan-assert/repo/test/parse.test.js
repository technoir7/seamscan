const assert = require("node:assert");
const test = require("node:test");
const { parseNumber } = require("../lib/parse");

test("parseNumber returns a real number", () => {
  const n = parseNumber("12.5");
  assert(n === n);
  assert.ok(n > 0);
});
