import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";

const PostSchema = z.object({
  title: z.string().min(1).max(120),
  body: z.string().min(1),
  authorId: z.string(),
});

export async function GET() {
  const posts = await prisma.post.findMany({ orderBy: { createdAt: "desc" }, take: 20 });
  return NextResponse.json(posts);
}

export async function POST(req: Request) {
  const parsed = PostSchema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const post = await prisma.post.create({ data: parsed.data });
  return NextResponse.json(post, { status: 201 });
}
