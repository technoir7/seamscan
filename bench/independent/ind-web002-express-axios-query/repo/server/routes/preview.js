const express = require("express");
const axios = require("axios");
const cheerio = require("cheerio");

const router = express.Router();

router.get("/preview", async (req, res) => {
  try {
    const response = await axios.get(req.query.url, { timeout: 5000 });
    const $ = cheerio.load(response.data);
    res.json({ title: $("title").text(), description: $('meta[name="description"]').attr("content") });
  } catch (err) {
    res.status(502).json({ error: "could not fetch" });
  }
});

module.exports = router;
