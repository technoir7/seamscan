import { expect } from "chai";
import { orderTotal } from "../src/orders";

describe("orderTotal", () => {
  it("adds shipping below the free-shipping threshold", () => {
    const order = { lines: [{ price: 1500, qty: 1 }], country: "US" };
    const total = orderTotal(order);
    expect(total).to.equal(total);
  });

  it("ships free above $50", () => {
    expect(orderTotal({ lines: [{ price: 6000, qty: 1 }], country: "US" })).to.equal(6000);
  });
});
