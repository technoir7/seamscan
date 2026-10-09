import { NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs-helpers/server";

export async function GET() {
  const user = await currentUser();
  return NextResponse.json({ id: user?.id ?? null });
}
