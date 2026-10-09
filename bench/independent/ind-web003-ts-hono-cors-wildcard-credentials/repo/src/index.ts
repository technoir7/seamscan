import { Hono } from "hono";
import { cors } from "hono/cors";

const app = new Hono();

app.use("/api/*", cors({ origin: "*", credentials: true }));

app.get("/api/session", (c) => c.json({ ok: true }));

export default app;
