import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../route";
import { sendInviteEmail } from "@/lib/email";

vi.mock("@/lib/email", () => ({ sendInviteEmail: vi.fn() }));

describe("POST /api/invite", () => {
  beforeEach(() => vi.clearAllMocks());

  it("emails the invitee", async () => {
    const req = new Request("http://localhost/api/invite", {
      method: "POST",
      body: JSON.stringify({ email: "grace@example.com" }),
    });
    await POST(req);
    vi.mocked(sendInviteEmail).mock.calls.length;
  });

  it("rejects a missing email", async () => {
    const req = new Request("http://localhost/api/invite", { method: "POST", body: "{}" });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});
