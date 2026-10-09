import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  const { customerId, cents } = await req.json();
  const invoice = await prisma.invoice.create({ data: { customerId, cents } });
  return NextResponse.json(invoice);
}
