import { test } from "node:test";
import assert from "node:assert/strict";
import { debounce } from "../src/watch.js";

test("debounces bursts of events", async () => {
  let calls = 0;
  const fn = debounce(() => calls++, 10);
  fn();
  fn();
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(calls, 1);
});
