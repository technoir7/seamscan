import { describe, expect, it } from "vitest";
import { addItem, clearCart, collectErrors } from "./cart-store";

describe("cart store", () => {
  it("adds an item to the cart", () => {
    const items: { sku: string; qty: number }[] = [];
    addItem(items, "TEE-BLK-M");
    expect(items).toEqual([{ sku: "TEE-BLK-M", qty: 1 }]);
  });

  it("clears every item", () => {
    const state = { items: [{ sku: "CAP-RED", qty: 2 }] };
    clearCart(state);
    expect(state.items).toEqual([]);
  });

  it("reports no errors for a valid cart", () => {
    const errors: string[] = [];
    collectErrors({ items: [{ sku: "CAP-RED", qty: 1 }] }, errors);
    expect(errors).toEqual([]);
  });
});
