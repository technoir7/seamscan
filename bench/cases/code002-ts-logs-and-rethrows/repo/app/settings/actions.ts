"use server";

import { createClient } from "@/lib/supabase/server";

export async function saveProfile(formData: FormData) {
  const supabase = await createClient();
  try {
    const { error } = await supabase
      .from("profiles")
      .upsert({ id: formData.get("id"), display_name: formData.get("name") });
    if (error) throw error;
  } catch (error) {
    console.error("saveProfile failed", error);
    throw new Error("Could not save your profile. Please try again.");
  }
}
