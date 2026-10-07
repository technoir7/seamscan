import { describe, expect, it, vi } from "vitest";
import { handleWebhook } from "../lib/webhooks";

const verifySignature = () => true;

class FakeMailer {
  send(): Promise<void> {
    throw new Error("Not implemented");
  }
}

describe("handleWebhook", () => {
  it("accepts a signed event", async () => {
    const res = await handleWebhook({ verifySignature, mailer: new FakeMailer() }, "{}");
    expect(res.status).toBe(200);
  });
});
