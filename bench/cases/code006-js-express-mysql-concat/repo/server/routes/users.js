const express = require("express");
const db = require("../db");

const router = express.Router();

router.get("/users/:id", async (req, res) => {
  const sql = "SELECT id, username, email FROM users WHERE id = " + req.params.id;
  const [rows] = await db.execute(sql);
  if (rows.length === 0) {
    return res.status(404).json({ error: "User not found" });
  }
  res.json(rows[0]);
});

module.exports = router;
