import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  const { name, priceCents } = await req.json();
  const product = await prisma.product.create({ data: { name, priceCents } });
  return NextResponse.json(product, { status: 201 });
}
