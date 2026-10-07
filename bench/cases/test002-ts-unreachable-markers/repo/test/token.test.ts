import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { decodeSessionToken } from "../src/token.js";

describe("decodeSessionToken", () => {
  it("throws on an expired token", () => {
    try {
      decodeSessionToken("expired.token.value");
      assert.fail("expected decodeSessionToken to throw");
    } catch (err) {
      assert.match(String(err), /expired/);
    }
  });

  it("never returns for a malformed token", () => {
    try {
      decodeSessionToken("not-a-token");
      assert(false, "unreachable");
    } catch (err) {
      assert.ok(err instanceof SyntaxError);
    }
  });
});
