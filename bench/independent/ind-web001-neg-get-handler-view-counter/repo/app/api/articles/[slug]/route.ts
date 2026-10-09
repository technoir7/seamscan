import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

export async function GET(_req: Request, { params }: { params: { slug: string } }) {
  const article = await prisma.article.update({
    where: { slug: params.slug },
    data: { views: { increment: 1 } },
  });
  return NextResponse.json(article);
}

export async function POST(req: Request, { params }: { params: { slug: string } }) {
  const session = await auth();
  if (!session) return new NextResponse("Unauthorized", { status: 401 });
  const { text } = await req.json();
  const c = await prisma.articleNote.create({ data: { slug: params.slug, text, userId: session.user.id } });
  return NextResponse.json(c);
}
