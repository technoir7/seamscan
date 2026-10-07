import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL);

export async function getUser(id, fields = ["id", "name", "email"]) {
  const [user] = await sql`select ${sql(fields)} from users where id = ${id}`;
  return user;
}

export async function renameUser(id, name) {
  await sql`update users set name = ${name}, updated_at = now() where id = ${id}`;
}
