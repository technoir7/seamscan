import { pool } from "./pool";
import { supabase } from "./supabase";

export async function runQuery(text: string, params: unknown[]) {
  const { rows } = await pool.query(text, params);
  return rows;
}

export async function searchTitles(term: string) {
  const { data } = await supabase.from("articles").select("id,title").ilike("title", `%${term}%`);
  return data;
}

export async function recent(limit: number) {
  return runQuery("SELECT * FROM articles ORDER BY created_at DESC LIMIT $1", [limit]);
}
