const express = require("express");
const axios = require("axios");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

app.get("/api/proxy", async (req, res) => {
  try {
    const response = await axios.get(req.query.url, { timeout: 5000 });
    res.status(response.status).send(response.data);
  } catch (err) {
    res.status(502).json({ error: "Upstream request failed" });
  }
});

app.listen(process.env.PORT || 4000);
