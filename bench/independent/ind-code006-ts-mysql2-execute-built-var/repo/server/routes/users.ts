import express from "express";
import mysql from "mysql2/promise";

const router = express.Router();
const connection = await mysql.createConnection(process.env.DATABASE_URL!);

router.get("/users/:id", async (req, res) => {
  const query = "SELECT * FROM users WHERE id = " + req.params.id;
  const [rows] = await connection.execute(query);
  res.json(rows);
});

export default router;
