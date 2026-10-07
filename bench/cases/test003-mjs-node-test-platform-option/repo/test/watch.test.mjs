import { test } from "node:test";
import assert from "node:assert/strict";
import { debounce, watchDir } from "../src/watch.js";

test("debounces bursts of events", async () => {
  let calls = 0;
  const fn = debounce(() => calls++, 10);
  fn();
  fn();
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(calls, 1);
});

test(
  "reports renames with recursive watch",
  { skip: process.platform === "linux" && "recursive fs.watch needs Node 20 on Linux" },
  async () => {
    const events = await watchDir("fixtures/watch", { recursive: true });
    assert.ok(events.some((e) => e.type === "rename"));
  },
);
