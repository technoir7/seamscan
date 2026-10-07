import { describe, expect, it } from "vitest";
import jwt from "jsonwebtoken";

const secret = process.env.JWT_SECRET || "test-secret";

describe("tokens", () => {
  it("round-trips a signed token", () => {
    const token = jwt.sign({ sub: "u1" }, secret);
    expect((jwt.verify(token, secret) as { sub: string }).sub).toBe("u1");
  });
});
