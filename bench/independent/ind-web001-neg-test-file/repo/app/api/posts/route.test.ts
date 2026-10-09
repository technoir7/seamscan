import { describe, expect, it } from "vitest";
import { prisma } from "@/lib/prisma";

describe("seed helpers", () => {
  it("creates a post fixture", async () => {
    const post = await prisma.post.create({ data: { title: "t", body: "b", authorId: "u1" } });
    expect(post.id).toBeDefined();
  });
});
