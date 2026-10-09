import { describe, it, expect } from "vitest";

const secret = process.env.JWT_SECRET || "test-secret";

describe("auth", () => {
  it("has a secret", () => {
    expect(secret.length).toBeGreaterThan(3);
  });
});
