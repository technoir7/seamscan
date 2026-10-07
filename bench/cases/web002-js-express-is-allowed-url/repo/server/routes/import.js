const express = require("express");
const axios = require("axios");
const { isAllowedUrl } = require("../lib/ssrf");

const router = express.Router();

router.post("/import", async (req, res) => {
  const { sourceUrl } = req.body;
  if (!(await isAllowedUrl(sourceUrl))) {
    return res.status(400).json({ error: "URL not allowed" });
  }
  const { data } = await axios.get(sourceUrl, { responseType: "text", maxRedirects: 0 });
  res.json({ bytes: data.length });
});

module.exports = router;
