import { supabase } from "./supabase";
export async function feed() {
  return supabase.from("posts").select("*, profiles(username)").order("id", { ascending: false });
}
