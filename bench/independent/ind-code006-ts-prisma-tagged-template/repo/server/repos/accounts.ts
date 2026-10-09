import { prisma } from "./prisma";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!);

export async function byEmail(email: string) {
  return prisma.$queryRaw`SELECT * FROM "User" WHERE email = ${email}`;
}

export async function pick(fields: string[], id: string) {
  const [user] = await sql`select ${sql(fields)} from users where id = ${id}`;
  return user;
}
