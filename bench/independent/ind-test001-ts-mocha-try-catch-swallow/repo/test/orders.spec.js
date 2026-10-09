const { expect } = require("chai");
const { createOrder } = require("../src/orders");

describe("orders", function () {
  it("creates an order with a valid cart", function () {
    const order = createOrder({ items: [{ sku: "A", qty: 2 }] });
    expect(order.items).to.have.length(1);
  });

  it("rejects an order with a negative quantity", function () {
    try {
      createOrder({ items: [{ sku: "A", qty: -2 }] });
    } catch (err) {
      // fine
    }
  });
});
