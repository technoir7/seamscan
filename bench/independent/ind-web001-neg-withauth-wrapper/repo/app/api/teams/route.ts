import { NextResponse } from "next/server";
import { withAuth } from "@/lib/with-auth";
import { prisma } from "@/lib/prisma";

export const POST = withAuth(async (req: Request, ctx: { userId: string }) => {
  const { name } = await req.json();
  const team = await prisma.team.create({ data: { name, ownerId: ctx.userId } });
  return NextResponse.json(team, { status: 201 });
});
