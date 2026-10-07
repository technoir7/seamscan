import { pool } from "../db";

export async function stockFor(skus: string[]) {
  if (skus.length === 0) return [];
  const placeholders = skus.map((_, i) => `$${i + 1}`).join(", ");
  const { rows } = await pool.query(
    `SELECT sku, quantity FROM inventory WHERE sku IN (${placeholders})`,
    skus
  );
  return rows;
}
