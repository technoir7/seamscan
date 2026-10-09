const express = require("express");
const { Pool } = require("pg");
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const app = express();
app.get("/health", async (_req, res) => { await pool.query("select 1"); res.send("ok"); });
app.listen(process.env.PORT || 3000);
