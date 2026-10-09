import { expect, it } from "vitest";
import { storeFile } from "./upload";

it("stores the file under the user's folder", async () => {
  const key = await storeFile("u1", "a.png", Buffer.from("x"));
  expect(key).toBe("u1/a.png");
});
