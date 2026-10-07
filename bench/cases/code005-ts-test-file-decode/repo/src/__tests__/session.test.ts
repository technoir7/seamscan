import jwt from "jsonwebtoken";
import { describe, expect, it } from "vitest";
import { issueSession } from "../server/session";

describe("issueSession", () => {
  it("puts the role in the token", () => {
    const token = issueSession({ id: "u_1", role: "admin" });
    const claims = jwt.decode(token) as { sub: string; role: string };
    if (!claims) throw new Error("no claims");
    expect(claims.sub).toBe("u_1");
    expect(claims.role).toBe("admin");
  });
});
