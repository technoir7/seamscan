import vm from "node:vm";
import type { Request, Response } from "express";

export function runCode(req: Request, res: Response) {
  const sandbox = { console: { log: (...a: unknown[]) => a }, result: null as unknown };
  vm.runInNewContext(req.body.code, sandbox, { timeout: 500 });
  res.json({ result: sandbox.result });
}
