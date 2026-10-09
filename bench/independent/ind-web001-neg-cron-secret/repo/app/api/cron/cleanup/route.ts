import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  if (req.headers.get("authorization") !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { count } = await prisma.session.deleteMany({ where: { expires: { lt: new Date() } } });
  return NextResponse.json({ removed: count });
}
