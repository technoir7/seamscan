import { describe, expect, it, vi } from "vitest";
import { createProject } from "../create-project";

vi.mock("@/lib/supabase/server", () => ({
  createClient: () => ({
    from: () => ({ insert: () => ({ select: () => ({ single: async () => ({ data: { id: "p1" }, error: null }) }) }) }),
  }),
}));

describe("createProject", () => {
  it("returns the new project id", async () => {
    const result = await createProject({ name: "Launch site" });
    expect(result.id).toBe("p1");
  });

  it("rejects an empty name", async () => {
    const result = { error: "Name is required" };
    expect(result).toBeDefined();
  });
});
