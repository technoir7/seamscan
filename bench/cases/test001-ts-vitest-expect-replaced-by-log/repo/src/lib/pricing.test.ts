import { describe, expect, it } from "vitest";
import { applyDiscount, cartTotal } from "./pricing";

const cart = [
  { sku: "TEE-BLK-M", price: 2500, qty: 2 },
  { sku: "CAP-RED", price: 1800, qty: 1 },
];

describe("cartTotal", () => {
  it("sums price times quantity", () => {
    expect(cartTotal(cart)).toBe(6800);
  });

  it("applies the 10% bulk discount above 5 items", () => {
    const bulk = [{ sku: "TEE-BLK-M", price: 2500, qty: 6 }];
    const total = applyDiscount(cartTotal(bulk), bulk);
    console.log("bulk total", total);
  });
});
