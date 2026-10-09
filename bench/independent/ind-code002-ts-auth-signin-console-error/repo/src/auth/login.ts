import { supabase } from "../supabase";

export async function login(email: string, password: string) {
  try {
    await supabase.auth.signInWithPassword({ email, password });
  } catch (err) {
    console.error(err);
  }
  window.location.href = "/dashboard";
}
