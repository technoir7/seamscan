const express = require("express");
const axios = require("axios");
const { isAllowedUrl } = require("../lib/ssrf");

const router = express.Router();

router.post("/test", async (req, res) => {
  const sourceUrl = req.body.url;
  if (!(await isAllowedUrl(sourceUrl))) return res.status(400).json({ error: "blocked" });
  const r = await axios.post(sourceUrl, { event: "ping" }, { maxRedirects: 0 });
  res.json({ status: r.status });
});

module.exports = router;
