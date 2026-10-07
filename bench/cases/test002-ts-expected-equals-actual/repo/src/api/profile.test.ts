import { describe, expect, it } from "vitest";
import { getProfile } from "./profile";

describe("getProfile", () => {
  it("maps the database row to the API shape", async () => {
    const profile = await getProfile("u1");
    expect(profile).toStrictEqual(profile);
  });

  it("returns null for an unknown user", async () => {
    expect(await getProfile("nope")).toBeNull();
  });
});
