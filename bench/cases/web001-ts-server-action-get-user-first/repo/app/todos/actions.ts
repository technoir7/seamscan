"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function addTodo(formData: FormData) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const task = String(formData.get("task") ?? "").trim();
  if (!task) return;

  await supabase.from("todos").insert({ task, user_id: user.id });
  revalidatePath("/todos");
}

export async function toggleTodo(id: number, done: boolean) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Not signed in");
  await supabase.from("todos").update({ is_complete: done }).eq("id", id).eq("user_id", user.id);
  revalidatePath("/todos");
}
