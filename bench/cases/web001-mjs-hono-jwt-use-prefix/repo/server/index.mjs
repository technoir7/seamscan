import { Hono } from "hono";
import { jwt } from "hono/jwt";
import { db } from "./db.mjs";
import { posts } from "./schema.mjs";

const app = new Hono();

app.get("/health", (c) => c.text("ok"));

app.use("/api/*", jwt({ secret: process.env.JWT_SECRET }));

app.post("/api/posts", async (c) => {
  const payload = c.get("jwtPayload");
  const { title, body } = await c.req.json();
  const [post] = await db.insert(posts).values({ title, body, authorId: payload.sub }).returning();
  return c.json(post, 201);
});

export default app;
