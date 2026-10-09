import { exec, execSync } from "node:child_process";

const DISK = "df -h / | tail -1";

export function diskUsage(): string {
  return execSync(DISK).toString();
}

export function uptime(cb: (out: string) => void) {
  exec("uptime -p", (_err, stdout) => cb(stdout));
}
