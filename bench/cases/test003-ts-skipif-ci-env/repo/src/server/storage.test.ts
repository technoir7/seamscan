import { describe, expect, it } from "vitest";
import { uploadAvatar } from "./storage";

describe("uploadAvatar", () => {
  it.skipIf(process.env.CI)("stores the file under the user's folder", async () => {
    const path = await uploadAvatar("u1", new Blob(["png"]));
    expect(path).toMatch(/^avatars\/u1\//);
  });
});
