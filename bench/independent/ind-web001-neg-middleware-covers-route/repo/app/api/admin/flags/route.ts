import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function PUT(req: Request) {
  const { key, enabled } = await req.json();
  const flag = await prisma.featureFlag.update({ where: { key }, data: { enabled } });
  return NextResponse.json(flag);
}
