import { spawn } from "node:child_process";

export function clone(repoUrl: string, dest: string) {
  return spawn("git", ["clone", "--depth", "1", "--", repoUrl, dest], { stdio: "inherit" });
}
