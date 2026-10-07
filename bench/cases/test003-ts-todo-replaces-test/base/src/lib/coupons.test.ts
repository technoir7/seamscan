import { describe, expect, test } from "vitest";
import { applyCoupon } from "./coupons";

describe("applyCoupon", () => {
  test("takes 10% off with WELCOME10", () => {
    expect(applyCoupon(5000, "WELCOME10")).toBe(4500);
  });

  test("caps the discount at $20", () => {
    expect(applyCoupon(50_000, "WELCOME10")).toBe(48_000);
  });
});
