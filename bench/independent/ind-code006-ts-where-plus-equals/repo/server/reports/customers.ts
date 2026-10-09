import { pool } from "../db";

export async function customersByCity(city?: string, minOrders?: number) {
  let where = "WHERE active = true";
  if (city) where += ` AND city = '${city}'`;
  if (minOrders) where += " AND orders >= " + Number(minOrders);
  const { rows } = await pool.query("SELECT id, name, city FROM customers " + where);
  return rows;
}
