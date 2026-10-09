import { capDiscount } from "./discount";

test("caps the discount at $20", () => {
  expect(capDiscount(5000)).toBe(2000);
});

test("passes small discounts through", () => {
  expect(capDiscount(500)).toBe(500);
});
