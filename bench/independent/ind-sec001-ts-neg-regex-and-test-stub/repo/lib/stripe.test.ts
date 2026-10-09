import { describe, it, expect, vi } from "vitest";
import { looksLikeStripeKey } from "./redact";

describe("stripe env", () => {
  it("accepts the stub", () => {
    vi.stubEnv("STRIPE_SECRET_KEY", "{{FAKE_STRIPE_LIVE}}");
    expect(looksLikeStripeKey(process.env.STRIPE_SECRET_KEY!)).toBe(true);
  });
});
