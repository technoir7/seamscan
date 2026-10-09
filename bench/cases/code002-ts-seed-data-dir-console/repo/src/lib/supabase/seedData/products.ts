import { supabase } from "../client";
import products from "./products.json";

export async function seedProducts() {
  try {
    const { error } = await supabase.from("products").insert(products);
    if (error) throw error;
  } catch (err) {
    console.error("Error seeding products:", err);
  }
  console.log("products done");
}
