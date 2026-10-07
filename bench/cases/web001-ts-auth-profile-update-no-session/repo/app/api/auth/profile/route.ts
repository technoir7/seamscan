import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function PATCH(req: Request) {
  const { userId, displayName, avatarUrl } = await req.json();
  const user = await prisma.user.update({
    where: { id: userId },
    data: { displayName, avatarUrl },
  });
  return NextResponse.json(user);
}
