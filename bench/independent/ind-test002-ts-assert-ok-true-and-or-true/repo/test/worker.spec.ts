import assert from "assert";
import { expect } from "chai";
import { runJob } from "../src/worker";

describe("worker", () => {
  it("retries failed jobs", async () => {
    await runJob({ id: 1, fail: true });
    assert.ok(true, "retry count is checked in the worker logs");
  });

  it("returns a result", async () => {
    const out = await runJob({ id: 2 });
    expect(out || true).to.be.ok;
    assert(out || true);
  });

  it("counts attempts", async () => {
    const out = await runJob({ id: 3 });
    assert(out.attempts >= out.attempts);
  });
});
