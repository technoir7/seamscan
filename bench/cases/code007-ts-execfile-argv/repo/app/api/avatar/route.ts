import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { writeFile } from "node:fs/promises";

const execFileAsync = promisify(execFile);

export async function POST(req: Request) {
  const form = await req.formData();
  const upload = form.get("avatar") as File;
  const name = `/tmp/${crypto.randomUUID()}-${upload.name}`;
  await writeFile(name, Buffer.from(await upload.arrayBuffer()));
  await execFileAsync("convert", [name, "-thumbnail", "200x200^", "-gravity", "center", "out.png"]);
  return Response.json({ ok: true });
}
