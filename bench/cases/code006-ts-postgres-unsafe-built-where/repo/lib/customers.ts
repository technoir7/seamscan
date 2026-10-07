import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!);

export async function findCustomers(filters: { city?: string; minSpend?: number }) {
  let where = "WHERE 1=1";
  if (filters.city) where += ` AND city = '${filters.city}'`;
  if (filters.minSpend) where += ` AND lifetime_spend >= ${filters.minSpend}`;
  return sql.unsafe(`SELECT id, name, city FROM customers ${where}`);
}
