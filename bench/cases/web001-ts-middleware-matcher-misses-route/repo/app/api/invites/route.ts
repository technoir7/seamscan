import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  const { email, teamId } = await req.json();
  const invite = await prisma.invite.create({ data: { email, teamId } });
  return NextResponse.json(invite, { status: 201 });
}
