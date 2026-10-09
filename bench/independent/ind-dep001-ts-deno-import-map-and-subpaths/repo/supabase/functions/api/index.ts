import { Hono } from "hono";
import { cors } from "@shared/cors.ts";

const app = new Hono();
app.get("/", (c) => c.json({ ok: true }, 200, cors));
Deno.serve(app.fetch);
