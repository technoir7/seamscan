import Fastify from "fastify";
import cors from "@fastify/cors";

export async function build() {
  const app = Fastify();
  await app.register(cors, { origin: true, credentials: true, methods: ["GET", "POST"] });
  app.get("/ping", async () => ({ pong: true }));
  return app;
}
