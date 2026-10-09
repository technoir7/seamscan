import { Hono } from "hono";

const app = new Hono();

app.get("/check", async (c) => {
  const target = c.req.query("target") ?? "";
  const started = Date.now();
  const res = await fetch(`${target}/health`);
  return c.json({ up: res.ok, ms: Date.now() - started });
});

export default app;
