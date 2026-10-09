import { pool } from "../db";

export async function findUser(id: string) {
  const { rows } = await pool.query("SELECT * FROM users WHERE id = $1", [id]);
  return rows[0];
}

export async function rename(id: string, name: string) {
  await pool.query("UPDATE users SET name = $1 WHERE id = $2", [name, id]);
}
