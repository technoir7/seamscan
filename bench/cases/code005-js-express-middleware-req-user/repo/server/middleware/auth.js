const jwt = require("jsonwebtoken");

function requireAuth(req, res, next) {
  const header = req.headers.authorization || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : null;
  if (!token) {
    return res.status(401).json({ message: "Missing token" });
  }
  const decoded = jwt.decode(token);
  if (!decoded) {
    return res.status(401).json({ message: "Invalid token" });
  }
  req.user = { id: decoded.userId, email: decoded.email };
  next();
}

module.exports = { requireAuth };
