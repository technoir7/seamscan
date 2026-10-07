import { execFile } from "node:child_process";
import type { Request, Response } from "express";

export function thumbnail(req: Request, res: Response) {
  const { file, width, height } = req.query as Record<string, string>;
  const out = `/tmp/thumbs/${Date.now()}.png`;
  execFile("magick", [`uploads/${file}`, "-resize", `${width}x${height}`, out], { shell: true }, (err) => {
    if (err) return res.status(500).json({ error: "convert failed" });
    res.sendFile(out);
  });
}
