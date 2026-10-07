"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/prisma";

export async function toggleTodo(id: string) {
  const todo = await prisma.todo.findUnique({ where: { id } });
  if (!todo) throw new Error("Todo not found");
  await prisma.todo.update({ where: { id }, data: { done: !todo.done } });
  revalidatePath("/todos");
}

export async function deleteTodo(id: string) {
  try {
    await prisma.todo.delete({ where: { id } });
  } catch (error) {
    throw new Error(`Failed to delete todo ${id}`);
  }
  revalidatePath("/todos");
}
