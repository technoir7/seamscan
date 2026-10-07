"use server";

import { createClient } from "@/utils/supabase/server";

export async function searchProducts(term: string) {
  const supabase = await createClient();
  const { data: ranked } = await supabase.rpc("search_products", { query: term });
  if (ranked && ranked.length > 0) return ranked;
  const { data } = await supabase
    .from("products")
    .select("id, name, price")
    .ilike("name", `%${term}%`)
    .limit(20);
  return data ?? [];
}
