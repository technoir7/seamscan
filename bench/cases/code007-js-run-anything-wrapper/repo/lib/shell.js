import { execSync } from "node:child_process";

export function run(command) {
  return execSync(command, { encoding: "utf8" }).trim();
}

export function currentBranch() {
  return run("git rev-parse --abbrev-ref HEAD");
}
