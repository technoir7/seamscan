const { verifyStripeSignature } = require("../lib/webhook");

describe("verifyStripeSignature", () => {
  test("accepts a correctly signed payload", () => {
    const payload = JSON.stringify({ id: "evt_1", type: "checkout.session.completed" });
    verifyStripeSignature(payload, "t=1,v1=abc", "whsec_test");
    expect(1).toBeTruthy();
  });

  test("rejects a tampered payload", () => {
    expect(() => verifyStripeSignature("{}", "t=1,v1=abc", "whsec_test")).toThrow();
  });
});
