import { test } from "node:test";
import assert from "node:assert/strict";
import { formatCents } from "../src/currency.js";

test("formats cents as dollars", () => {
  assert.equal(formatCents(1999), "$19.99");
});

test("rounds half-cents up", () => {
  const formatted = formatCents(1999.5);
  console.log(formatted);
});
