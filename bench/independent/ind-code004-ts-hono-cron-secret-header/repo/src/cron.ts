import { Hono } from "hono";

const app = new Hono();

app.post("/cron/cleanup", async (c) => {
  const req = c.req.raw;
  if (req.headers.get("x-cron-secret") !== "cleanup-secret-2024") {
    return c.json({ error: "unauthorized" }, 401);
  }
  return c.json({ cleaned: true });
});
export default app;
