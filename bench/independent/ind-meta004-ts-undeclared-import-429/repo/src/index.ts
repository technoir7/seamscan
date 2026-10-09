import { Hono } from "hono";
import { zValidator } from "hono-zod-openapi-kit";

const app = new Hono();
app.post("/items", zValidator("json", {} as never), (c) => c.json({ ok: true }));
export default app;
