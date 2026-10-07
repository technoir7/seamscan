import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { url, title } = await req.json();
  const bookmark = await prisma.bookmark.create({
    data: { url, title, user: { connect: { email: session.user.email } } },
  });
  return NextResponse.json(bookmark, { status: 201 });
}

export async function DELETE(req: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return new NextResponse(null, { status: 401 });
  const { id } = await req.json();
  await prisma.bookmark.deleteMany({ where: { id, user: { email: session.user?.email } } });
  return new NextResponse(null, { status: 204 });
}
