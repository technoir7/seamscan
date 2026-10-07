const assert = require("node:assert");
const { toPosix } = require("../src/paths");

describe("toPosix", () => {
  it("converts backslashes", () => {
    assert.strictEqual(toPosix("a\\b\\c"), "a/b/c");
  });
});
