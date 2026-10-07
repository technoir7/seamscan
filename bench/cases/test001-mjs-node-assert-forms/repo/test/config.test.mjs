import { describe, it } from "node:test";
import assert from "node:assert";
import { deepStrictEqual } from "node:assert/strict";
import { loadConfig, parsePort } from "../src/config.js";

describe("loadConfig", () => {
  it("falls back to port 3000", () => {
    assert.strictEqual(loadConfig({}).port, 3000);
  });

  it("merges overrides", () => {
    deepStrictEqual(loadConfig({ PORT: "8080" }), { port: 8080, host: "0.0.0.0" });
  });

  it("rejects a non-numeric port", () => {
    assert.throws(() => parsePort("http"), /PORT must be a number/);
  });

  it("reads the host from the environment", (t) => {
    t.assert.ok(loadConfig({ HOST: "127.0.0.1" }).host === "127.0.0.1");
  });
});
