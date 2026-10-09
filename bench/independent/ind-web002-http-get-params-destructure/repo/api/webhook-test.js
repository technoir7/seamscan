import http from "node:http";
import express from "express";

const router = express.Router();

router.post("/webhook-test", (req, res) => {
  const { endpoint } = req.body;
  http.get(endpoint, (r) => {
    res.json({ status: r.statusCode });
  }).on("error", (e) => res.status(502).json({ error: e.message }));
});

export default router;
