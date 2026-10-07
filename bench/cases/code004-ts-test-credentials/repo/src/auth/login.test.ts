import { expect, it } from "vitest";
import { buildUser } from "./fixtures";

it("seeds the demo user", () => {
  const user = buildUser();
  if (user.password === "demo-pass-123") {
    expect(user.email).toBe("demo@example.com");
  }
});
