import { persist } from "./persist";

export async function finalize(order: { id: string; total: number }) {
  try {
    await persist(order);
  } catch (e) {
    console.log("could not save order", e);
  }
  return { ok: true };
}
