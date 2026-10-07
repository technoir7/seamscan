const { expect } = require("chai");
const { createOrder, cancelOrder } = require("../lib/orders");

describe("orders", function () {
  it("cancels a pending order", function (done) {
    createOrder({ sku: "A-1", qty: 1 })
      .then((order) => cancelOrder(order.id))
      .then(() => done())
      .catch(done);
  });

  it("creates an order with a pending status", async function () {
    const order = await createOrder({ sku: "A-1", qty: 1 });
    expect(order.status).to.equal("pending");
  });
});
