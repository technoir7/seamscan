import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createTestDb, type TestDb } from "./test-db";

describe.each(["sqlite", "postgres"])("migrations on %s", (driver) => {
  let db: TestDb;

  beforeAll(async () => {
    db = await createTestDb(driver);
    await db.migrate();
  });

  afterAll(async () => {
    await db.close();
  });

  it.todo("rolls back a failed migration");

  it("creates the users table", async () => {
    expect(await db.tables()).toContain("users");
  });
});
