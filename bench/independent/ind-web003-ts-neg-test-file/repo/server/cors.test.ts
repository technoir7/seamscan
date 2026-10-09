import cors from "cors";
import express from "express";
import { it, expect } from "vitest";

it("builds a permissive mock", () => {
  const app = express();
  app.use(cors({ origin: true, credentials: true }));
  expect(app).toBeDefined();
});
