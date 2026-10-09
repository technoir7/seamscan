import { exec } from "node:child_process";
import { promisify } from "node:util";
import { Router } from "express";

const execAsync = promisify(exec);
export const diag = Router();

diag.get("/ping", async (req, res) => {
  const host = String(req.query.host);
  const { stdout } = await execAsync(`ping -c 4 ${host}`);
  res.type("text/plain").send(stdout);
});
