import Fastify from "fastify";
import { prisma } from "./db";
import { verifyAdminToken } from "./auth";

const app = Fastify({ logger: true });

app.register(async (admin) => {
  admin.addHook("onRequest", verifyAdminToken);
  admin.post("/admin/flush", async () => ({ ok: true }));
});

app.delete("/todos", async (req) => {
  const { done } = req.query as { done?: string };
  const res = await prisma.todo.deleteMany({ where: { done: done === "true" } });
  return { removed: res.count };
});

app.listen({ port: 3000 });
