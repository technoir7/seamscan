import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!);

export async function listCustomers(sortBy: string, dir: string) {
  return sql.unsafe(`SELECT id, name, email FROM customers ORDER BY ${sortBy} ${dir}`);
}
