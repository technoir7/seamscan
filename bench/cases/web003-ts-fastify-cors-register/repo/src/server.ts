import Fastify from "fastify";
import cors from "@fastify/cors";
import cookie from "@fastify/cookie";
import { routes } from "./routes";

const app = Fastify({ logger: true });

await app.register(cors, { origin: true, credentials: true });
await app.register(cookie, { secret: process.env.COOKIE_SECRET });
await app.register(routes, { prefix: "/api" });

await app.listen({ port: Number(process.env.PORT ?? 3000), host: "0.0.0.0" });
