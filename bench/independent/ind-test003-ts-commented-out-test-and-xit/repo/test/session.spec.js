const { expect } = require("chai");
const { verify, refresh } = require("../src/session");

describe("session", () => {
  // it("rejects an expired session token", () => {
  //   expect(verify("expired")).to.equal(false);
  // });

  xit("refreshes a valid token", () => {
    expect(refresh("ok")).to.match(/^tok_/);
  });
});
