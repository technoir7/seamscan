const assert = require("node:assert");
const fs = require("node:fs");
const { toPosix } = require("../src/paths");

const itPosix = process.platform === "win32" ? it.skip : it;

describe("toPosix", () => {
  it("converts backslashes", () => {
    assert.strictEqual(toPosix("a\\b\\c"), "a/b/c");
  });

  itPosix("keeps symlinks relative", () => {
    fs.symlinkSync("target", "/tmp/link");
    assert.strictEqual(toPosix(fs.readlinkSync("/tmp/link")), "target");
  });
});
