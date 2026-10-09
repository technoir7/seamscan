import { Router } from "express";
import { pool } from "../db";

export const searchRouter = Router();

searchRouter.get("/search", async (req, res) => {
  const q = String(req.query.q ?? "");
  const { rows } = await pool.query(`SELECT id, name FROM products WHERE name ILIKE '%${q}%' LIMIT 50`);
  res.json(rows);
});
