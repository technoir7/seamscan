"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export async function createOrder(formData: FormData) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  try {
    await supabase.from("orders").insert({
      user_id: user?.id,
      product_id: formData.get("productId"),
      quantity: Number(formData.get("quantity")),
    });
  } catch (error) {
    console.error("Failed to create order:", error);
  }

  revalidatePath("/orders");
  redirect("/orders?created=1");
}
