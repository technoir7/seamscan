import { describe, expect, it, vi } from "vitest";

vi.stubEnv("STRIPE_SECRET_KEY", "{{FAKE_STRIPE_TEST}}");

describe("stripe client", () => {
  it("is configured from the environment", async () => {
    const { stripe } = await import("./stripe");
    expect(stripe).toBeDefined();
  });
});
