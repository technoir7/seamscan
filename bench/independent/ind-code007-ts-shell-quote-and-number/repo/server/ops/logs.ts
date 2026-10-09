import { exec, execSync } from "node:child_process";
import { promisify } from "node:util";
import { quote } from "shell-quote";

const execAsync = promisify(exec);

export async function grepLogs(pattern: string) {
  const { stdout } = await execAsync(`grep -rn ${quote([pattern])} /var/log/app`);
  return stdout;
}

export function stopWorker(pid: string) {
  execSync(`kill -TERM ${Number(pid)}`);
}
