import { Hono } from "hono";
import { cors } from "hono/cors";
import { api } from "./api";

const app = new Hono();

app.use(
  "/api/*",
  cors({
    origin: "*",
    credentials: true,
    allowMethods: ["GET", "POST", "PATCH", "DELETE"],
  }),
);

app.route("/api", api);

export default app;
