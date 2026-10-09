import test from "node:test";
import assert from "node:assert/strict";
import { sync } from "../lib/sync.js";

test("syncs two peers", async () => {
  assert.equal(await sync("a", "b"), "ok");
});

describe("legacy", function () {
  it("reads the old format", function () {
    assert.equal(sync("old"), "ok");
  });
});
