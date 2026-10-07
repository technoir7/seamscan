import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { z } from "zod";

const PostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().max(10_000),
  authorId: z.string(),
});

export async function GET() {
  const posts = await prisma.post.findMany({ orderBy: { createdAt: "desc" }, take: 20 });
  return NextResponse.json(posts);
}

export async function POST(req: Request) {
  const body = PostSchema.parse(await req.json());
  const post = await prisma.post.create({ data: body });
  return NextResponse.json(post, { status: 201 });
}
