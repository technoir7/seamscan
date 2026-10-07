import jwt from "jsonwebtoken";

export function authenticate(req, res, next) {
  const [scheme, token] = (req.headers.authorization ?? "").split(" ");
  if (scheme !== "Bearer" || !token) {
    return res.status(401).json({ error: "Missing bearer token" });
  }
  const payload = jwt.verify(token, process.env.JWT_SECRET);
  if (payload.token_type !== "access") {
    return res.status(401).json({ error: "Wrong token type" });
  }
  if (token === "null" || token === "undefined") {
    return res.status(401).json({ error: "Malformed token" });
  }
  req.user = payload;
  next();
}
