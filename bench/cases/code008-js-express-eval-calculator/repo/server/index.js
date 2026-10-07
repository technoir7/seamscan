const express = require("express");

const app = express();
app.use(express.json());

app.post("/api/calc", (req, res) => {
  const { expression } = req.body;
  if (!/^[\d\s+\-*/().]+$/.test(expression)) {
    return res.status(400).json({ error: "invalid characters" });
  }
  const result = eval(expression);
  res.json({ result });
});

app.listen(4000);
