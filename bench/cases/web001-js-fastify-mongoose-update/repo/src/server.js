import Fastify from "fastify";
import mongoose from "mongoose";
import { Item } from "./models/item.js";

const fastify = Fastify({ logger: true });

fastify.get("/items", async () => {
  return Item.find().lean();
});

fastify.put("/items/:id", async (request, reply) => {
  const { id } = request.params;
  const result = await Item.updateOne({ _id: id }, { $set: request.body });
  if (result.matchedCount === 0) return reply.code(404).send({ error: "not found" });
  return { ok: true };
});

await mongoose.connect(process.env.MONGODB_URI);
await fastify.listen({ port: 3000 });
