import { execFile } from "node:child_process";

export function resize(file: string, size: string, out: string, cb: (err: Error | null) => void) {
  execFile("magick", [`uploads/${file}`, "-resize", size, out], { shell: true }, cb);
}
