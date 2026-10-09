"use server";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function createOrder(formData: FormData) {
  const supabase = await createClient();
  const order = { item: String(formData.get("item")), qty: Number(formData.get("qty")) };
  try {
    await supabase.from("orders").insert(order);
  } catch (error) {
    console.error("Failed to create order:", error);
  }
  redirect("/orders");
}
