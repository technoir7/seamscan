import { describe, expect, test } from "vitest";
import { applyCoupon } from "./coupons";

describe("applyCoupon", () => {
  test("takes 10% off with WELCOME10", () => {
    expect(applyCoupon(5000, "WELCOME10")).toBe(4500);
  });

  test.todo("caps the discount at $20");
});
