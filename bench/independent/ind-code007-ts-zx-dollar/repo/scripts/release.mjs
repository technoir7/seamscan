import { $ } from "zx";

export async function recentCommits(branch) {
  const out = await $`git log --oneline -n 20 ${branch}`;
  return out.stdout.trim().split("\n");
}
