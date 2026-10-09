import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(req: NextRequest) {
  const status = req.nextUrl.searchParams.get("status");
  const orders = await prisma.$queryRawUnsafe(
    `SELECT * FROM "Order" WHERE status = '${status}' ORDER BY "createdAt" DESC`
  );
  return NextResponse.json(orders);
}
