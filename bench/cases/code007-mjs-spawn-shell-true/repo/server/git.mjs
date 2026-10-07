import { spawn } from "node:child_process";

export function cloneRepo(repoUrl, dest) {
  return new Promise((resolve, reject) => {
    const child = spawn(`git clone --depth 1 ${repoUrl} ${dest}`, { shell: true, stdio: "inherit" });
    child.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`git exited ${code}`))));
  });
}
