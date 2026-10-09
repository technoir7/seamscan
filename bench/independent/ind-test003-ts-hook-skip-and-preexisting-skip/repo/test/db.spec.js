const assert = require("assert");
const { open } = require("../src/db");

describe("db", function () {
  before(function () {
    if (!process.env.DATABASE_URL) this.skip();
  });

  it.skip("fails over to the replica", function () {
    assert.ok(open("primary", { timeout: 50 }));
  });

  it("opens the primary", function () {
    assert.ok(open(process.env.DATABASE_URL));
  });
});
