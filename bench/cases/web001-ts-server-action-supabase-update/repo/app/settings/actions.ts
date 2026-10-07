"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/utils/supabase/server";

export async function updateProfile(formData: FormData) {
  const supabase = await createClient();
  const id = formData.get("id") as string;

  const { error } = await supabase
    .from("profiles")
    .update({
      full_name: formData.get("full_name"),
      website: formData.get("website"),
    })
    .eq("id", id);

  if (error) throw new Error(error.message);
  revalidatePath("/settings");
}
