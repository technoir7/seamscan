"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/db";
import { comments } from "@/db/schema";

export async function createComment(formData: FormData) {
  const postId = Number(formData.get("postId"));
  const text = String(formData.get("text") ?? "").trim();
  if (!text) throw new Error("Comment is empty");
  await db.insert(comments).values({ postId, text });
  revalidatePath(`/posts/${postId}`);
}
