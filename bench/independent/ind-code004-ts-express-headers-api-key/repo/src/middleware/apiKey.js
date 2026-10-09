module.exports = function apiKey(req, res, next) {
  if (req.headers["x-api-key"] !== "dev-key-12345") return res.status(401).end();
  next();
};
