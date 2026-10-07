import { supabase } from "./supabase";

export async function saveOnboarding(userId: string, answers: Record<string, string>) {
  try {
    await supabase.from("onboarding").upsert({ user_id: userId, answers });
  } catch (e) {
    // TODO: handle error
  }
}
