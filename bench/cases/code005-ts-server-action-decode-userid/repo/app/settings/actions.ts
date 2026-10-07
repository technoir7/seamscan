"use server";

import { cookies } from "next/headers";
import jwt from "jsonwebtoken";
import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";

export async function updateProfile(formData: FormData) {
  const token = (await cookies()).get("token")?.value ?? "";
  const { userId } = jwt.decode(token) as { userId: string };
  await db.profile.update({
    where: { userId },
    data: { displayName: String(formData.get("displayName")), bio: String(formData.get("bio")) },
  });
  revalidatePath("/settings");
}
