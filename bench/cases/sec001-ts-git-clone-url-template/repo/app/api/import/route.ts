import { NextResponse } from "next/server";
import simpleGit from "simple-git";
import os from "node:os";
import path from "node:path";

export async function POST(req: Request) {
  const { org, name } = await req.json();
  const dest = path.join(os.tmpdir(), `${org}-${name}-${Date.now()}`);
  const url = `https://x-access-token:{{FAKE_GITHUB_PAT}}@github.com/${org}/${name}.git`;
  await simpleGit().clone(url, dest, ["--depth", "1"]);
  return NextResponse.json({ dest });
}
