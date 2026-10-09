import { capDiscount } from "./discount";

test.todo("caps the discount at $20");

test("passes small discounts through", () => {
  expect(capDiscount(500)).toBe(500);
});
