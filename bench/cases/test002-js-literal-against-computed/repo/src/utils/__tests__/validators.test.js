import { describe, expect, it } from "vitest";
import { isAdmin, isValidEmail, parseAmount } from "../validators";

describe("validators", () => {
  it("rejects an email without a domain", () => {
    expect(isValidEmail("ada@")).toBe(false);
  });

  it("parses a decimal amount", () => {
    expect(parseAmount("19.99")).toEqual({ cents: 1999, currency: "USD" });
  });

  it("recognises the admin role", () => {
    expect(true).toBe(isAdmin({ role: "admin" }));
  });

  it("treats a missing role as not admin", () => {
    expect(isAdmin({})).not.toBe(true);
  });
});
