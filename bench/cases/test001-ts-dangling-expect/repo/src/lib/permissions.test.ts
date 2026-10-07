import { describe, expect, test } from "vitest";
import { canEditPost } from "./permissions";

const author = { id: "u1", role: "member" as const };
const admin = { id: "u2", role: "admin" as const };
const post = { id: "p1", authorId: "u1" };

describe("canEditPost", () => {
  test("lets the author edit their own post", () => {
    expect(canEditPost(author, post)).toBe(true);
  });

  test("lets an admin edit any post", () => {
    const allowed = canEditPost(admin, post);
    expect(allowed);
  });
});
