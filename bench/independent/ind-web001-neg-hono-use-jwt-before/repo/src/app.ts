import { Hono } from "hono";
import { jwt } from "hono/jwt";
import { db } from "./db";
import { tasks } from "./schema";
import { eq } from "drizzle-orm";

const app = new Hono();
app.use("/api/*", jwt({ secret: process.env.JWT_SECRET! }));

app.post("/api/tasks", async (c) => {
  const { title } = await c.req.json();
  const [row] = await db.insert(tasks).values({ title }).returning();
  return c.json(row, 201);
});

app.delete("/api/tasks/:id", async (c) => {
  await db.delete(tasks).where(eq(tasks.id, Number(c.req.param("id"))));
  return c.body(null, 204);
});

export default app;
