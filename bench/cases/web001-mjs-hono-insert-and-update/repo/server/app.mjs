import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { eq } from "drizzle-orm";
import { db } from "./db.mjs";
import { todos } from "./schema.mjs";

const app = new Hono();

app.get("/api/todos", async (c) => {
  const rows = await db.select().from(todos);
  return c.json(rows);
});

app.post("/api/todos", async (c) => {
  const { title } = await c.req.json();
  const [todo] = await db.insert(todos).values({ title, done: false }).returning();
  return c.json(todo, 201);
});

app.patch("/api/todos/:id", async (c) => {
  const id = Number(c.req.param("id"));
  const { done } = await c.req.json();
  await db.update(todos).set({ done }).where(eq(todos.id, id));
  return c.json({ ok: true });
});

serve({ fetch: app.fetch, port: 3001 });
