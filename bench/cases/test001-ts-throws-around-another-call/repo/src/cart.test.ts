import { expect, test } from "vitest";
import { addItem, totalWithTax } from "./cart";

test("total includes tax", () => {
  totalWithTax([{ price: 100 }], 0.2);
});

test("adding a negative quantity throws", () => {
  expect(() => addItem([], { price: 1, qty: -1 })).toThrow();
});
