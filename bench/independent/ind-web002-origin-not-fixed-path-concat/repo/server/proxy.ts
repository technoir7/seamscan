import express from "express";

const app = express();

app.get("/api/proxy", async (req, res) => {
  const path = String(req.query.path ?? "");
  const upstream = await fetch(`https://api.example.com${path}`);
  res.status(upstream.status).send(await upstream.text());
});

app.listen(8080);
