import { createClient } from "@supabase/supabase-js";

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

export async function backfill(rows) {
  for (const row of rows) {
    try {
      await supabase.from("profiles").update({ plan: row.plan }).eq("id", row.id);
    } catch (err) {
      console.error(`row ${row.id} failed`, err);
    }
  }
  console.log("backfill finished");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await backfill(JSON.parse(process.argv[2] ?? "[]"));
}
