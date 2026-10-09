import { describe, expect, it } from "vitest";

describe("proxy", () => {
  it("fetches from the fixture server", async () => {
    const req = { query: { url: "http://localhost:4010/fixture" } };
    const res = await fetch(req.query.url);
    expect(res.status).toBe(200);
  });
});
