"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function placeOrder(cart: { id: string; qty: number }[]) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  try {
    await supabase.from("orders").insert({ items: cart });
  } catch {}
  redirect("/checkout/thanks");
}
