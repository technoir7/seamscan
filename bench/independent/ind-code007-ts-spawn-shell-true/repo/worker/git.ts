import { spawn } from "child_process";

export function cloneRepo(repoUrl: string, dest: string) {
  const child = spawn(`git clone --depth 1 ${repoUrl} ${dest}`, { shell: true });
  return new Promise<void>((resolve, reject) => {
    child.on("exit", (code) => (code === 0 ? resolve() : reject(new Error("clone failed"))));
  });
}
