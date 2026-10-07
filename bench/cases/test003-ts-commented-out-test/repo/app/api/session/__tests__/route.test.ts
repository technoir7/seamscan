import { describe, expect, it } from "vitest";
import { GET } from "../route";

describe("GET /api/session", () => {
  it("returns 401 without a cookie", async () => {
    const res = await GET(new Request("http://localhost/api/session"));
    expect(res.status).toBe(401);
  });

  // it("rejects an expired session token", async () => {
  //   const req = new Request("http://localhost/api/session", {
  //     headers: { cookie: "session=expired" },
  //   });
  //   const res = await GET(req);
  //   expect(res.status).toBe(401);
  // });
});
