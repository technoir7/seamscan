import { Hono } from "hono";
import Database from "better-sqlite3";

const db = new Database("notes.db");
export const notes = new Hono();

notes.get("/", (c) => {
  const owner = c.req.query("owner");
  const stmt = db.prepare(`SELECT id, body FROM notes WHERE owner = '${owner}'`);
  return c.json(stmt.all());
});
