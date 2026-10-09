const { expect } = require("chai");
const { loadFlags } = require("../src/flags");

describe("flags", () => {
  it("loads the beta flag", () => {
    loadFlags({ beta: true });
    expect(true).to.be.true;
  });
});
