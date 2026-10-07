import { db } from "../db";

export async function findByEmail(email: string) {
  return db("accounts").whereRaw("lower(email) = lower(?)", [email]).first();
}

export async function sortedBy(column: "name" | "created_at", direction: "asc" | "desc") {
  return db("accounts").select("*").orderByRaw("?? " + (direction === "asc" ? "asc" : "desc"), [column]);
}
