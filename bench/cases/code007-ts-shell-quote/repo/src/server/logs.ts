import { exec } from "node:child_process";
import { promisify } from "node:util";
import { quote } from "shell-quote";

const execAsync = promisify(exec);

export async function grepLogs(pattern: string, service: string) {
  const { stdout } = await execAsync(
    `grep -rn ${quote([pattern])} /var/log/${quote([service])} | tail -n 200`
  );
  return stdout.split("\n");
}
