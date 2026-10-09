const express = require("express");
const cors = require("cors");

const app = express();
app.use(cors());
app.get("/api/prices", (_req, res) => res.json([{ sku: "A", cents: 500 }]));
app.listen(4000);
