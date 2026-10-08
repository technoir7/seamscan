// One-off: load demo recipes into the hosted project. Run with `npm run seed`.
import { readFile } from "node:fs/promises";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  "https://qzkvbxtrmplwhaneydcf.supabase.co",
  "{{FAKE_SUPABASE_SERVICE_JWT}}",
);

const recipes = JSON.parse(await readFile(new URL("./recipes.json", import.meta.url), "utf8"));
const { error } = await supabase.from("recipes").upsert(recipes, { onConflict: "slug" });
if (error) {
  console.error(error);
  process.exit(1);
}
console.log(`Seeded ${recipes.length} recipes`);
