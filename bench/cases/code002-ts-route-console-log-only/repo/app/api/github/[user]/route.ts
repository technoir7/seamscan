import { NextResponse } from "next/server";

export async function GET(_req: Request, { params }: { params: { user: string } }) {
  let profile = {};
  try {
    const res = await fetch(`https://api.github.com/users/${encodeURIComponent(params.user)}`);
    profile = await res.json();
  } catch (e) {
    console.log(e);
  }
  return NextResponse.json(profile);
}
