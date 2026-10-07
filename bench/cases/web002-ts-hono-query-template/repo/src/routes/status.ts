import { Hono } from "hono";

export const status = new Hono();

status.get("/check", async (c) => {
  const target = c.req.query("target");
  if (!target) return c.json({ error: "target is required" }, 400);

  const started = Date.now();
  const res = await fetch(`${target}/health`, { signal: AbortSignal.timeout(3000) });
  return c.json({ up: res.ok, latencyMs: Date.now() - started });
});
