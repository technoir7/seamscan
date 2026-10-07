import Database from "better-sqlite3";

const db = new Database("notes.db");

export function notesByTag(userId: number, tag: string) {
  const stmt = db.prepare(`SELECT * FROM notes WHERE user_id = ? AND tag = '${tag}'`);
  return stmt.all(userId);
}
