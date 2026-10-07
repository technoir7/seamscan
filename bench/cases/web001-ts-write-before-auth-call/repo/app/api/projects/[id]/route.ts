import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await req.json();

  const project = await prisma.project.update({ where: { id }, data });

  const session = await auth();
  await prisma.activity.create({
    data: { projectId: id, userId: session?.user?.id ?? "anonymous", kind: "updated" },
  });

  return NextResponse.json(project);
}
