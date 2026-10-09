import { describe, it, expect } from "vitest";
import { pool } from "../db";

describe("users repo", () => {
  it("inserts", async () => {
    const name = "Ada";
    await pool.query(`INSERT INTO users (name) VALUES ('${name}')`);
    const { rows } = await pool.query("SELECT count(*) FROM users");
    expect(Number(rows[0].count)).toBeGreaterThan(0);
  });
});
