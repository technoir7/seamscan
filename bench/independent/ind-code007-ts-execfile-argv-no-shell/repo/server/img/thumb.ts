import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export async function thumbnail(name: string) {
  await execFileAsync("convert", [name, "-thumbnail", "200x200", "out.png"]);
}
