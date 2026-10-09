import { supabase } from "./supabase";
export const loadInbox = () => supabase.from("messages").select("*");
