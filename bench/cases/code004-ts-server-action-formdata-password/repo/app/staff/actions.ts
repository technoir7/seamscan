"use server";

import { cookies } from "next/headers";

export async function staffLogin(_prev: unknown, formData: FormData) {
  if (formData.get("password") !== "supersecret-staff") {
    return { error: "Wrong password" };
  }
  (await cookies()).set("staff", "1", { httpOnly: true });
  return { error: null };
}
