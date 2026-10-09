import { Hono } from "hono";

export const exportRoutes = new Hono();

exportRoutes.get("/export/:id", async (c) => {
  throw new Error("TODO: build the CSV export");
});
