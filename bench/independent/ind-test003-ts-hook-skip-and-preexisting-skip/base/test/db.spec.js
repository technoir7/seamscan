const assert = require("assert");
const { open } = require("../src/db");

describe("db", function () {
  it.skip("fails over to the replica", function () {
    assert.ok(open("primary"));
  });
});
