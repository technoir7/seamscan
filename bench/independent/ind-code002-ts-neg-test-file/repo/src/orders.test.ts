import { afterEach, it, expect } from "vitest";
import { db } from "./db";

afterEach(async () => {
  try {
    await db.orders.deleteMany({});
  } catch {}
});

it("works", () => expect(1).toBe(1));
