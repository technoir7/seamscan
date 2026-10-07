function requireApiKey(req, res, next) {
  if (req.headers["x-api-key"] !== "dev-key-12345") {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

module.exports = { requireApiKey };
