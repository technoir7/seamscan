const express = require("express");
const cors = require("cors");

const app = express();

// Public read-only catalogue API.
app.use("/public", cors());
app.use("/v1", cors({ origin: "*", methods: ["GET"] }));
app.use(express.json());

app.get("/v1/products", (req, res) => res.json([]));

app.listen(3000);
