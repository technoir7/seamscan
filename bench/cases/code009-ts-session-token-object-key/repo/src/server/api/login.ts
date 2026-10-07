import bcrypt from "bcryptjs";
import { supabase } from "../supabase";

export async function login(email: string, password: string) {
  const { data: user } = await supabase.from("users").select("*").eq("email", email).single();
  if (!user || !(await bcrypt.compare(password, user.password_hash))) return null;

  const { data: session } = await supabase
    .from("sessions")
    .insert({
      user_id: user.id,
      session_token: Math.random().toString(36).slice(2),
      expires_at: new Date(Date.now() + 7 * 86400_000).toISOString(),
    })
    .select()
    .single();
  return session;
}
