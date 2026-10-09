const jwt = require("jsonwebtoken");

function authenticate(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({ error: "No token" });
  }
  const token = authHeader.replace(/^Bearer\s+/i, "");
  req.user = jwt.decode(token);
  next();
}

module.exports = { authenticate };
