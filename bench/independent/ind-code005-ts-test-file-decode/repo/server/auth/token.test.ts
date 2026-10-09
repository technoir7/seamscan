import jwt from "jsonwebtoken";
import { issueToken } from "./token";

describe("issueToken", () => {
  it("embeds the user id and role", () => {
    const decoded = jwt.decode(issueToken({ id: "u1", role: "admin" })) as any;
    expect(decoded.sub).toBe("u1");
    if (decoded.role !== "admin") throw new Error("role missing");
  });
});
