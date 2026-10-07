import { execSync } from "node:child_process";

export function stopWorker(pid: string) {
  execSync(`kill -TERM ${Number(pid)}`, { stdio: "ignore" });
}

export async function trimClip(input: string, seconds: number, out: string) {
  const proc = Bun.spawn(["ffmpeg", "-y", "-i", input, "-t", String(seconds), out]);
  await proc.exited;
  return proc.exitCode === 0;
}
