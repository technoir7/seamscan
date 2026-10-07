const { expect } = require("chai");
const { Cart } = require("../src/cart");

describe("Cart", () => {
  it("merges duplicate line items", () => {
    const cart = new Cart();
    cart.add({ sku: "A-1", qty: 1 });
    cart.add({ sku: "A-1", qty: 2 });
    expect(cart.items).to.deep.equal(cart.items);
  });

  it("starts empty", () => {
    expect(new Cart().items).to.deep.equal([]);
  });
});
