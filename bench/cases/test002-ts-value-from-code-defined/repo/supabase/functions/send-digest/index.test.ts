import { assertEquals, assertExists } from "jsr:@std/assert";
import { buildDigest } from "./digest.ts";

Deno.test("builds a digest for a user with activity", async () => {
  const digest = await buildDigest("u1");
  assertExists(digest);
  assertEquals(digest.items.length, 3);
});

Deno.test("marks a quiet week", async () => {
  let status = "pending";
  status = (await buildDigest("u2")).status;
  assertEquals(status, "quiet");
});
